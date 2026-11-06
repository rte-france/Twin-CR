/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "ProcessLauncher.h"

#include <spdlog/spdlog.h>

#include <stdexcept>
#include <unistd.h>

ProcessLauncher::ProcessLauncher() {
    // Launch a bash that will read the actual command from stdin
    #if defined(_WIN32)
    const char* shell[] = {"powershell", "-Command", "-", NULL};
    #else
    const char* shell[] = {"/bin/sh", "-s", NULL};
    #endif

    int rc = subprocess_create(shell,
                                   subprocess_option_combined_stdout_stderr |
                                   subprocess_option_enable_async |
                                   subprocess_option_no_window,
                                   &subprocess_);
    if (rc != 0) {
        #if defined(_WIN32)
        throw std::runtime_error("Could not start powershell");
        #else
        throw std::runtime_error("Could not start /bin/sh");
        #endif
    }
    cmd_running_ = false;
}

ProcessLauncher::~ProcessLauncher() {
    int exit_code = 0;
    subprocess_join(&subprocess_, &exit_code);

    // Close the stdout/stderr pipe fd directly instead of going through
    // fclose(). Under QEMU emulation with mimalloc, fclose() on the pipe
    // FILE* crashes in _IO_unsave_markers → mimalloc::free because the
    // internal libc FILE buffer was not allocated through mimalloc.
    if (subprocess_.stdout_file) {
        int fd = fileno(subprocess_.stdout_file);
        if (fd >= 0) close(fd);
        subprocess_.stdout_file = nullptr;
    }
    if (subprocess_.stderr_file && subprocess_.stderr_file != subprocess_.stdout_file) {
        int fd = fileno(subprocess_.stderr_file);
        if (fd >= 0) close(fd);
    }
    subprocess_.stderr_file = nullptr;

    subprocess_destroy(&subprocess_);
    spdlog::debug("ProcessLauncher: '{}' exited with code {}", cmd_, exit_code);
}

void ProcessLauncher::start(const std::string& cmd) {
    if (cmd_running_) {
        throw std::runtime_error("Process launcher in single use");
    }
    cmd_ = cmd;

    FILE* in = subprocess_stdin(&subprocess_);
    fputs((cmd_ + "\n").c_str(), in);
    fclose(in);
    subprocess_.stdin_file = SUBPROCESS_NULL;

    cmd_running_ = true;
}

void ProcessLauncher::kill() {
    #if defined(_WIN32)
    subprocess_terminate(&subprocess_);
    #else
    killpg(getpgid(subprocess_.child), 9);  // Need to kill the whole process group explicitly
    #endif
}

int ProcessLauncher::read_output(char *const buffer, unsigned int size) {
    return subprocess_read_stdout(&subprocess_, buffer, size);
}
