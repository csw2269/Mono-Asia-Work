#include "proc_client.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <thread>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pluto {
namespace {

template <typename T>
void append_bytes(std::vector<std::uint8_t>& out, const T* p, std::size_t count) {
    const auto* b = reinterpret_cast<const std::uint8_t*>(p);
    out.insert(out.end(), b, b + sizeof(T) * count);
}

std::size_t pipe_payload_size(std::int32_t n) {
    using namespace protocol;
    return sizeof(RequestHeader) +
           static_cast<std::size_t>(n) * kCategoricalPerUnit * sizeof(std::int64_t) +
           static_cast<std::size_t>(n) * kContinuousPerUnit * sizeof(float) +
           static_cast<std::size_t>(n) * 2 +
           kActionCount + kArgCount +
           kGlobalCount * sizeof(float) +
           kSpatialU16Bytes + kStaticU8Bytes +
           kHistoryCount * sizeof(std::int64_t);
}

} // namespace

bool valid_feature_batch(const FeatureBatch& b, std::int32_t max_units) {
    if (!protocol::valid_request_header(b.header, max_units)) return false;
    return b.unit_i64 && b.unit_f32 && b.unit_mask_a && b.unit_mask_b &&
           b.action_mask && b.arg_mask && b.globals &&
           b.spatial_u16 && b.static_u8 && b.history_i64;
}

bool serialize_feature_batch_to_shm(
    std::uint8_t* shm,
    std::size_t shm_size,
    const FeatureBatch& b,
    std::uint32_t request_seq) {
    using namespace protocol;
    if (!shm || shm_size < kShmSize || !valid_feature_batch(b, static_cast<std::int32_t>(kMaxUnitsCap)))
        return false;

    const std::size_t n = static_cast<std::size_t>(b.header.n);
    std::memcpy(shm + shm_off::request_header, &b.header, sizeof(b.header));
    std::memcpy(shm + shm_off::unit_i64, b.unit_i64, n * kCategoricalPerUnit * sizeof(std::int64_t));
    std::memcpy(shm + shm_off::unit_f32, b.unit_f32, n * kContinuousPerUnit * sizeof(float));
    std::memcpy(shm + shm_off::unit_mask_a, b.unit_mask_a, n);
    std::memcpy(shm + shm_off::unit_mask_b, b.unit_mask_b, n);
    std::memcpy(shm + shm_off::action_mask, b.action_mask, kActionCount);
    std::memcpy(shm + shm_off::arg_mask, b.arg_mask, kArgCount);
    std::memcpy(shm + shm_off::globals, b.globals, kGlobalCount * sizeof(float));
    std::memcpy(shm + shm_off::spatial_u16, b.spatial_u16, kSpatialU16Bytes);
    std::memcpy(shm + shm_off::static_u8, b.static_u8, kStaticU8Bytes);
    std::memcpy(shm + shm_off::history_i64, b.history_i64, kHistoryCount * sizeof(std::int64_t));
    protocol::store_pod(shm, shm_off::request_seq, request_seq);
    return true;
}

std::vector<std::uint8_t> serialize_feature_batch_to_pipe(const FeatureBatch& b) {
    using namespace protocol;
    if (!valid_feature_batch(b, static_cast<std::int32_t>(kMaxUnitsCap))) return {};

    const std::size_t n = static_cast<std::size_t>(b.header.n);
    std::vector<std::uint8_t> out;
    out.reserve(pipe_payload_size(b.header.n));
    append_bytes(out, &b.header, 1);
    append_bytes(out, b.unit_i64, n * kCategoricalPerUnit);
    append_bytes(out, b.unit_f32, n * kContinuousPerUnit);
    append_bytes(out, b.unit_mask_a, n);
    append_bytes(out, b.unit_mask_b, n);
    append_bytes(out, b.action_mask, kActionCount);
    append_bytes(out, b.arg_mask, kArgCount);
    append_bytes(out, b.globals, kGlobalCount);
    append_bytes(out, b.spatial_u16, static_cast<std::size_t>(kSpatialWidth) * kSpatialHeight);
    append_bytes(out, b.static_u8, static_cast<std::size_t>(kSpatialWidth) * kSpatialHeight);
    append_bytes(out, b.history_i64, kHistoryCount);
    return out;
}

struct ProcClient::Impl {
    bool ok = false;
    bool retryable = true;
    bool use_shm = false;
    std::uint32_t req_seq = 0;
    std::int64_t qpc_freq = 0;
    std::int32_t fps = 0;
    std::int32_t max_units = 0;
    std::int64_t model_version = 0;
    std::string model;
    std::string engine;
    std::string err;

#ifdef _WIN32
    HANDLE process = nullptr;
    HANDLE req_write = nullptr;
    HANDLE resp_read = nullptr;
    HANDLE mapping = nullptr;
    HANDLE req_event = nullptr;
    HANDLE resp_event = nullptr;
    std::uint8_t* shm = nullptr;
#endif
};

ProcClient::ProcClient() : impl_(std::make_unique<Impl>()) {
#ifdef _WIN32
    LARGE_INTEGER f{};
    if (QueryPerformanceFrequency(&f)) impl_->qpc_freq = f.QuadPart;
#else
    impl_->qpc_freq = 1000000000LL;
#endif
}

ProcClient::~ProcClient() { shutdown(); }

#ifdef _WIN32
namespace {

void close_handle(HANDLE& h) {
    if (h) {
        CloseHandle(h);
        h = nullptr;
    }
}

bool env_nonzero(const char* name, bool default_value) {
    const char* v = std::getenv(name);
    if (!v) return default_value;
    return v[0] != '0';
}

std::wstring quoted(const std::wstring& s) {
    return L"\"" + s + L"\"";
}

bool drive_absolute(const std::wstring& p) {
    return p.size() >= 2 &&
           ((p[0] >= L'A' && p[0] <= L'Z') || (p[0] >= L'a' && p[0] <= L'z')) &&
           p[1] == L':';
}

std::string winerr_text(DWORD e) {
    char buf[64]{};
    std::snprintf(buf, sizeof(buf), "error %lu", static_cast<unsigned long>(e));
    return buf;
}

bool write_all(HANDLE h, const void* p, std::size_t n) {
    const auto* cur = static_cast<const std::uint8_t*>(p);
    while (n) {
        DWORD wrote = 0;
        const DWORD chunk = static_cast<DWORD>(std::min<std::size_t>(n, 0x7fffffff));
        if (!WriteFile(h, cur, chunk, &wrote, nullptr) || wrote == 0) return false;
        cur += wrote;
        n -= wrote;
    }
    return true;
}

bool read_all(HANDLE h, void* p, std::size_t n) {
    auto* cur = static_cast<std::uint8_t*>(p);
    while (n) {
        DWORD got = 0;
        const DWORD chunk = static_cast<DWORD>(std::min<std::size_t>(n, 0x7fffffff));
        if (!ReadFile(h, cur, chunk, &got, nullptr) || got == 0) return false;
        cur += got;
        n -= got;
    }
    return true;
}

DWORD deadline_wait_ms(std::int64_t now, std::int64_t deadline, std::int64_t freq) {
    if (deadline <= now || freq <= 0) return 0;
    const long double ticks = static_cast<long double>(deadline - now);
    const long double ms = ticks * 1000.0L / static_cast<long double>(freq);
    if (ms >= static_cast<long double>(INFINITE - 1)) return INFINITE - 1;
    const auto ceil_ms = static_cast<DWORD>(ms);
    return (static_cast<long double>(ceil_ms) < ms) ? ceil_ms + 1 : ceil_ms;
}

} // namespace
#endif

bool ProcClient::start(const std::wstring& exe_path,
                       const std::string& log_path,
                       std::uint32_t handshake_timeout_ms) {
    shutdown();
    impl_->retryable = true;
    impl_->err.clear();

#ifndef _WIN32
    (void)exe_path;
    (void)log_path;
    (void)handshake_timeout_ms;
    impl_->retryable = false;
    impl_->err = "ProcClient::start is Windows-only";
    return false;
#else
    SECURITY_ATTRIBUTES sa{};
    sa.nLength = sizeof(sa);
    sa.bInheritHandle = TRUE;

    HANDLE req_read = nullptr, req_write = nullptr;
    HANDLE resp_read = nullptr, resp_write = nullptr;
    HANDLE log_file = nullptr;
    HANDLE parent_wait = nullptr;
    HANDLE mapping = nullptr, req_event = nullptr, resp_event = nullptr;
    std::uint8_t* shm = nullptr;

    auto cleanup_locals = [&]() {
        close_handle(req_read); close_handle(req_write);
        close_handle(resp_read); close_handle(resp_write);
        close_handle(log_file); close_handle(parent_wait);
        if (shm) { UnmapViewOfFile(shm); shm = nullptr; }
        close_handle(mapping); close_handle(req_event); close_handle(resp_event);
    };

    if (!CreatePipe(&req_read, &req_write, &sa, 0)) {
        impl_->err = "CreatePipe(req) failed (" + winerr_text(GetLastError()) + ")";
        cleanup_locals();
        return false;
    }
    if (!CreatePipe(&resp_read, &resp_write, &sa, 0)) {
        impl_->err = "CreatePipe(resp) failed (" + winerr_text(GetLastError()) + ")";
        cleanup_locals();
        return false;
    }
    if (!SetHandleInformation(req_write, HANDLE_FLAG_INHERIT, 0) ||
        !SetHandleInformation(resp_read, HANDLE_FLAG_INHERIT, 0)) {
        impl_->err = "SetHandleInformation failed (" + winerr_text(GetLastError()) + ")";
        cleanup_locals();
        return false;
    }

    // SHM setup failure is intentionally silent: current Pluto falls back to pipes.
    if (env_nonzero("BWRL_SHM", true)) {
        mapping = CreateFileMappingA(INVALID_HANDLE_VALUE, &sa, PAGE_READWRITE, 0,
                                     protocol::kShmSize, nullptr);
        if (mapping) {
            shm = static_cast<std::uint8_t*>(
                MapViewOfFile(mapping, FILE_MAP_ALL_ACCESS, 0, 0, protocol::kShmSize));
        }
        if (shm) {
            protocol::init_shm_static_header(shm, protocol::kShmSize);
            req_event = CreateEventA(&sa, FALSE, FALSE, nullptr);
            resp_event = CreateEventA(&sa, FALSE, FALSE, nullptr);
        }
        if (shm && req_event && resp_event) {
            if (!DuplicateHandle(GetCurrentProcess(), GetCurrentProcess(),
                                 GetCurrentProcess(), &parent_wait,
                                 SYNCHRONIZE, TRUE, 0)) {
                parent_wait = nullptr;
            }
        }
        if (!(shm && req_event && resp_event && parent_wait)) {
            if (shm) { UnmapViewOfFile(shm); shm = nullptr; }
            close_handle(mapping); close_handle(req_event); close_handle(resp_event);
            close_handle(parent_wait);
        }
    }

    log_file = CreateFileA(log_path.c_str(), GENERIC_WRITE, FILE_SHARE_READ, &sa,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (log_file == INVALID_HANDLE_VALUE) {
        log_file = nullptr;
        impl_->err = "CreateFile(log) failed (" + winerr_text(GetLastError()) + ")";
        cleanup_locals();
        return false;
    }

    auto set_handle_env = [](const char* name, HANDLE h) {
        char buf[32]{};
        std::snprintf(buf, sizeof(buf), "%llu",
                      static_cast<unsigned long long>(reinterpret_cast<std::uintptr_t>(h)));
        SetEnvironmentVariableA(name, buf);
    };
    auto clear_shm_env = []() {
        SetEnvironmentVariableA("PLUTO_SHM_SEC", nullptr);
        SetEnvironmentVariableA("PLUTO_SHM_REQ_EV", nullptr);
        SetEnvironmentVariableA("PLUTO_SHM_RESP_EV", nullptr);
        SetEnvironmentVariableA("PLUTO_SHM_PARENT", nullptr);
    };

    if (shm) {
        set_handle_env("PLUTO_SHM_SEC", mapping);
        set_handle_env("PLUTO_SHM_REQ_EV", req_event);
        set_handle_env("PLUTO_SHM_RESP_EV", resp_event);
        set_handle_env("PLUTO_SHM_PARENT", parent_wait);
    }

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdInput = req_read;
    si.hStdOutput = resp_write;
    si.hStdError = log_file;
    PROCESS_INFORMATION pi{};

    auto run_create = [&](const std::wstring& app) -> bool {
        std::wstring cmd = quoted(app);
        std::vector<wchar_t> mutable_cmd(cmd.begin(), cmd.end());
        mutable_cmd.push_back(L'\0');
        return CreateProcessW(app.c_str(), mutable_cmd.data(),
                              nullptr, nullptr, TRUE, CREATE_NO_WINDOW,
                              nullptr, nullptr, &si, &pi) != FALSE;
    };

    bool created = run_create(exe_path);
    DWORD create_err = created ? ERROR_SUCCESS : GetLastError();
    if (!created && exe_path.size() >= 0xF8 && drive_absolute(exe_path)) {
        const std::wstring long_path = L"\\\\?\\" + exe_path;
        created = run_create(long_path);
        create_err = created ? ERROR_SUCCESS : GetLastError();
    }

    clear_shm_env();
    close_handle(parent_wait);
    close_handle(req_read);
    close_handle(resp_write);
    close_handle(log_file);

    if (!created) {
        std::string suffix;
        if (create_err == ERROR_FILE_NOT_FOUND || create_err == ERROR_PATH_NOT_FOUND)
            suffix = " = exe not found";
        else if (create_err == ERROR_BAD_EXE_FORMAT)
            suffix = " = bad exe format; 32-bit-only Wine prefix?";
        impl_->err = "CreateProcess failed (error " + std::to_string(create_err) + suffix + ")";
        impl_->retryable = !(create_err == ERROR_FILE_NOT_FOUND ||
                             create_err == ERROR_PATH_NOT_FOUND ||
                             create_err == ERROR_BAD_EXE_FORMAT);
        cleanup_locals();
        return false;
    }

    CloseHandle(pi.hThread);
    impl_->process = pi.hProcess;
    impl_->req_write = req_write; req_write = nullptr;
    impl_->resp_read = resp_read; resp_read = nullptr;
    impl_->mapping = mapping; mapping = nullptr;
    impl_->req_event = req_event; req_event = nullptr;
    impl_->resp_event = resp_event; resp_event = nullptr;
    impl_->shm = shm; shm = nullptr;

    const DWORD start_tick = GetTickCount();
    protocol::PlutoHandshake hs{};
    for (;;) {
        const DWORD wait = WaitForSingleObject(impl_->process, 100);
        DWORD avail = 0;
        if (!PeekNamedPipe(impl_->resp_read, nullptr, 0, nullptr, &avail, nullptr)) {
            const DWORD e = GetLastError();
            impl_->err = "stdout pipe broke before handshake (error " + std::to_string(e) + ")";
            shutdown();
            return false;
        }
        if (avail >= sizeof(hs)) {
            if (!read_all(impl_->resp_read, &hs, sizeof(hs))) {
                impl_->err = "handshake read failed (error " + std::to_string(GetLastError()) + ")";
                shutdown();
                return false;
            }
            break;
        }
        if (wait == WAIT_OBJECT_0) {
            DWORD code = 0;
            if (GetExitCodeProcess(impl_->process, &code))
                impl_->err = "server exited before handshake; server exited (code " + std::to_string(code) + ")";
            else
                impl_->err = "server exited before handshake";
            shutdown();
            return false;
        }
        if (static_cast<DWORD>(GetTickCount() - start_tick) > handshake_timeout_ms) {
            impl_->err = "no handshake within " + std::to_string(handshake_timeout_ms) +
                         " ms (server hung loading? see pluto_infer.log)";
            shutdown();
            return false;
        }
    }

    if (hs.magic != protocol::kHandshakeMagic ||
        hs.version != static_cast<std::int32_t>(protocol::kProtocolVersion) ||
        hs.frames_per_step <= 0 || hs.max_units <= 0) {
        char buf[128]{};
        std::snprintf(buf, sizeof(buf), "bad handshake (magic 0x%08lx version %ld)",
                      static_cast<unsigned long>(hs.magic), static_cast<long>(hs.version));
        impl_->err = buf;
        impl_->retryable = false;
        shutdown();
        return false;
    }
    if (hs.max_units > static_cast<std::int32_t>(protocol::kMaxUnitsCap)) {
        impl_->err = "handshake max_units " + std::to_string(hs.max_units) +
                     " exceeds protocol cap " + std::to_string(protocol::kMaxUnitsCap);
        impl_->retryable = false;
        shutdown();
        return false;
    }

    impl_->fps = hs.frames_per_step;
    impl_->max_units = hs.max_units;
    impl_->model_version = hs.model_version;
    impl_->model.assign(hs.model, strnlen(hs.model, sizeof(hs.model)));
    impl_->engine.assign(hs.engine, strnlen(hs.engine, sizeof(hs.engine)));
    if (impl_->model.empty()) impl_->model = "model v" + std::to_string(hs.model_version);

    impl_->use_shm = impl_->shm &&
        protocol::load_pod<std::uint32_t>(impl_->shm, protocol::shm_off::engine_ack) ==
            protocol::kShmMagic;
    impl_->ok = true;
    return true;
#endif
}

bool ProcClient::send_features(const FeatureBatch& batch) {
    if (!impl_->ok || !valid_feature_batch(batch, impl_->max_units)) return false;
#ifdef _WIN32
    const std::uint32_t next = impl_->req_seq + 1u;
    if (impl_->use_shm) {
        if (!serialize_feature_batch_to_shm(impl_->shm, protocol::kShmSize, batch, next)) return false;
        impl_->req_seq = next;
        if (!SetEvent(impl_->req_event)) {
            impl_->err = "SetEvent(req) failed (error " + std::to_string(GetLastError()) + ")";
            shutdown();
            return false;
        }
        return true;
    }

    auto bytes = serialize_feature_batch_to_pipe(batch);
    if (bytes.empty() || !write_all(impl_->req_write, bytes.data(), bytes.size())) {
        impl_->err = "pipe I/O failed (error " + std::to_string(GetLastError()) + ")";
        shutdown();
        return false;
    }
    impl_->req_seq = next;
    return true;
#else
    (void)batch;
    return false;
#endif
}

PollResult ProcClient::poll_or_recv(protocol::EngineResponse& out,
                                    std::int64_t deadline_qpc,
                                    bool lockstep) {
    out = protocol::EngineResponse{0, 0, 0, -1, -1000.0f, 0.0f};
    if (!impl_->ok) return PollResult::Error;

#ifdef _WIN32
    if (impl_->use_shm) {
        for (;;) {
            if (protocol::load_pod<std::uint32_t>(impl_->shm, protocol::shm_off::response_seq) ==
                impl_->req_seq) {
                std::memcpy(&out, impl_->shm + protocol::shm_off::response, sizeof(out));
                return PollResult::Ready;
            }

            const auto now = qpc_now();
            if (!lockstep && now >= deadline_qpc) return PollResult::NotReady;
            const DWORD wait_ms = lockstep ? INFINITE :
                deadline_wait_ms(now, deadline_qpc, impl_->qpc_freq);

            HANDLE hs[2]{impl_->resp_event, impl_->process};
            const DWORD r = WaitForMultipleObjects(2, hs, FALSE, wait_ms);
            if (r == WAIT_OBJECT_0 || r == WAIT_TIMEOUT) continue;
            if (r == WAIT_OBJECT_0 + 1) {
                DWORD code = 0;
                if (GetExitCodeProcess(impl_->process, &code))
                    impl_->err = "server exited (code " + std::to_string(code) + ")";
                else
                    impl_->err = "server process signaled";
                shutdown();
                return PollResult::Error;
            }
            impl_->err = "shm wait failed (error " + std::to_string(GetLastError()) + ")";
            shutdown();
            return PollResult::Error;
        }
    }

    for (;;) {
        DWORD avail = 0;
        if (!PeekNamedPipe(impl_->resp_read, nullptr, 0, nullptr, &avail, nullptr)) {
            impl_->err = "pipe I/O failed (error " + std::to_string(GetLastError()) + ")";
            shutdown();
            return PollResult::Error;
        }
        if (avail >= sizeof(out)) {
            if (!read_all(impl_->resp_read, &out, sizeof(out))) {
                impl_->err = "pipe I/O failed (error " + std::to_string(GetLastError()) + ")";
                shutdown();
                return PollResult::Error;
            }
            return PollResult::Ready;
        }
        if (!lockstep && qpc_now() >= deadline_qpc) return PollResult::NotReady;
        // Exact tiny-spin instruction sequence is not promoted from external analysis;
        // yielding here preserves nonblocking semantics without claiming byte parity.
        SwitchToThread();
    }
#else
    (void)deadline_qpc;
    (void)lockstep;
    return PollResult::Error;
#endif
}

void ProcClient::shutdown() {
#ifdef _WIN32
    if (impl_->shm && impl_->process) {
        const std::uint32_t one = 1;
        protocol::store_pod(impl_->shm, protocol::shm_off::quit, one);
        if (impl_->req_event) SetEvent(impl_->req_event);
    }

    close_handle(impl_->req_write);
    close_handle(impl_->resp_read);

    if (impl_->process) {
        const DWORD w = WaitForSingleObject(impl_->process, 3000);
        if (w == WAIT_TIMEOUT) TerminateProcess(impl_->process, 1);
        close_handle(impl_->process);
    }

    if (impl_->shm) {
        UnmapViewOfFile(impl_->shm);
        impl_->shm = nullptr;
    }
    close_handle(impl_->mapping);
    close_handle(impl_->req_event);
    close_handle(impl_->resp_event);
#endif
    impl_->use_shm = false;
    impl_->req_seq = 0;
    impl_->ok = false;
    impl_->fps = 0;
    impl_->max_units = 0;
}

bool ProcClient::ok() const noexcept { return impl_->ok; }
bool ProcClient::retryable() const noexcept { return impl_->retryable; }
bool ProcClient::using_shm() const noexcept { return impl_->use_shm; }
std::uint32_t ProcClient::request_seq() const noexcept { return impl_->req_seq; }
std::int32_t ProcClient::frames_per_step() const noexcept { return impl_->fps; }
std::int32_t ProcClient::max_units() const noexcept { return impl_->max_units; }

std::int64_t ProcClient::qpc_now() const noexcept {
#ifdef _WIN32
    LARGE_INTEGER q{};
    QueryPerformanceCounter(&q);
    return q.QuadPart;
#else
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
#endif
}

std::int64_t ProcClient::qpc_frequency() const noexcept { return impl_->qpc_freq; }
const std::string& ProcClient::model() const noexcept { return impl_->model; }
const std::string& ProcClient::engine() const noexcept { return impl_->engine; }
const std::string& ProcClient::error() const noexcept { return impl_->err; }

} // namespace pluto
