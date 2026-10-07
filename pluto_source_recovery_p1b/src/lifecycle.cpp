#include "lifecycle.hpp"

#include <algorithm>
#include <cstdlib>
#include <vector>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <mmsystem.h>
#endif

namespace pluto {
namespace {

bool env_on(const char* name) {
    const char* v = std::getenv(name);
    return v && *v && *v != '0';
}

} // namespace

LifecycleConfig read_lifecycle_environment() {
    LifecycleConfig cfg{};
    if (env_on("BWRL_LOCKSTEP")) cfg.mode = PacingMode::Lockstep;
    else if (env_on("BWRL_STRADDLE")) cfg.mode = PacingMode::Straddle;

    if (const char* v = std::getenv("BWRL_FRAME_BUDGET_MS")) {
        cfg.frame_budget_ms = std::max(5.0, std::atof(v));
    }
    cfg.draw = env_on("BWRL_DRAW");
    cfg.stdout_enabled = env_on("BWRL_STDOUT");
    return cfg;
}

std::wstring resolve_engine_path(void* module_handle) {
#ifndef _WIN32
    (void)module_handle;
    return {};
#else
    const HMODULE h = static_cast<HMODULE>(module_handle);
    std::size_t cap = 0x104;
    for (; cap <= 0x8000; cap *= 2) {
        std::vector<wchar_t> buf(cap, L'\0');
        const DWORD n = GetModuleFileNameW(h, buf.data(), static_cast<DWORD>(buf.size()));
        if (n == 0) return {};
        if (n < buf.size() - 1 || (n < buf.size() && GetLastError() != ERROR_INSUFFICIENT_BUFFER)) {
            std::wstring p(buf.data(), n);
            const auto slash = p.find_last_of(L"\\/");
            if (slash == std::wstring::npos) return {};
            p.resize(slash + 1);
            p += L"pluto\\pluto_infer.exe";
            return p;
        }
    }
    return {};
#endif
}

bool module_start_engine(BwrlModuleStub& module) {
    module.config = read_lifecycle_environment();
    module.fatal_error.clear();
    module.engine_up = false;

#ifdef _WIN32
    timeBeginPeriod(1);
#endif

    module.client.shutdown();
    const std::wstring exe = resolve_engine_path(module.module_handle);
    if (exe.empty()) {
        module.fatal_error = "exe path resolution failed";
        return false;
    }

    for (int attempt = 1; attempt <= 9; ++attempt) {
        if (module.client.start(exe, "pluto_infer.log", 180000)) {
            module.engine_up = true;
            return true;
        }
        if (attempt == 9 || !module.client.retryable()) break;
#ifdef _WIN32
        Sleep(750);
#else
        break;
#endif
    }

    module.fatal_error = module.client.error();
    return false;
}

void module_stop_engine(BwrlModuleStub& module) {
    module.client.shutdown();
    module.engine_up = false;
#ifdef _WIN32
    timeEndPeriod(1);
#endif
}

} // namespace pluto
