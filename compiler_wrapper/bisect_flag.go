// Copyright 2019 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"os"
	"path/filepath"
)

// Note: We keep this code in python as golang has no builtin
// shlex function.
const bisectPythonCommand = `
import bisect_driver
import shlex
import sys

def ExpandArgs(args, target):
	for arg in args:
		if arg[0] == '@':
			with open(arg[1:], 'rb') as f:
				ExpandArgs(shlex.split(f.read()), target)
		else:
			target.append(arg)
	return target

stage = sys.argv[1]
dir = sys.argv[2]
execargs = ExpandArgs(sys.argv[3:], [])

sys.exit(bisect_driver.bisect_driver(stage, dir, execargs))
`

func getBisectStage(env env) string {
	value, _ := env.getenv("BISECT_STAGE")
	return value
}

func calcBisectCommand(env env, cfg *config, bisectStage string, compilerCmd *command) (*command, error) {
	bisectDir, _ := env.getenv("BISECT_DIR")
	if bisectDir == "" {
		if cfg.isAndroidWrapper {
			homeDir, err := os.UserHomeDir()
			if err != nil {
				return nil, err
			}
			bisectDir = filepath.Join(homeDir, "ANDROID_BISECT")
		} else {
			bisectDir = "/tmp/sysroot_bisect"
		}
	}
	absCompilerPath := getAbsCmdPath(env, compilerCmd)
	return &command{
		Path: "/usr/bin/env",
		Args: append([]string{
			"python",
			"-c",
			bisectPythonCommand,
			bisectStage,
			bisectDir,
			absCompilerPath,
		}, compilerCmd.Args...),
		EnvUpdates: compilerCmd.EnvUpdates,
	}, nil
}