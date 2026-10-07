#pragma once
#include "proc_client.hpp"

#include <string>

namespace pluto {

enum class PacingMode : int {
    Block = 0,
    Straddle = 1,
    Lockstep = 2,
};

struct LifecycleConfig {
    PacingMode mode = PacingMode::Block;
    double frame_budget_ms = 40.0;
    bool draw = false;
    bool stdout_enabled = false;
};

LifecycleConfig read_lifecycle_environment();
std::wstring resolve_engine_path(void* module_handle);

struct BwrlModuleStub {
    void* module_handle = nullptr;
    ProcClient client;
    LifecycleConfig config{};
    bool engine_up = false;
    std::string fatal_error;
};

bool module_start_engine(BwrlModuleStub& module);
void module_stop_engine(BwrlModuleStub& module);

} // namespace pluto
