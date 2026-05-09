#!/usr/bin/env python
# Copyright 2014 the V8 project authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This program wraps an arbitrary command since gn currently can only execute
scripts."""

from __future__ import print_function

import os
import shutil
import subprocess
import sys
import tempfile


def _is_mksnapshot(cmd):
  """Detect if we're invoking the mksnapshot binary."""
  return len(cmd) > 0 and 'mksnapshot' in os.path.basename(cmd[0])


def _run_mksnapshot_via_tmp(cmd):
  """Run mksnapshot with output redirected through /tmp to work around
  C++ fopen() failures on Docker bind-mounted Windows (NTFS) volumes.
  The binary writes to /tmp successfully; we then copy to the real paths."""
  new_cmd = list(cmd)
  # Map of tmp_path -> real_path for output file args
  output_map = {}
  OUTPUT_FLAGS = ('--embedded_src', '--startup_src')

  i = 0
  while i < len(new_cmd):
    if new_cmd[i] in OUTPUT_FLAGS and i + 1 < len(new_cmd):
      real_path = new_cmd[i + 1]
      ext = os.path.splitext(real_path)[1] or '.tmp'
      tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, dir='/tmp')
      os.close(tmp_fd)
      output_map[tmp_path] = real_path
      new_cmd[i + 1] = tmp_path
    i += 1

  result = subprocess.call(new_cmd)

  if result == 0:
    for tmp_path, real_path in output_map.items():
      dest_dir = os.path.dirname(os.path.abspath(real_path))
      if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
      shutil.copy2(tmp_path, real_path)
  # Always clean up temp files
  for tmp_path in output_map:
    try:
      os.remove(tmp_path)
    except OSError:
      pass

  return result


cmd = sys.argv[1:]

if _is_mksnapshot(cmd):
  result = _run_mksnapshot_via_tmp(cmd)
else:
  result = subprocess.call(cmd)

if result != 0:
  # Windows error codes such as 0xC0000005 and 0xC0000409 are much easier
  # to recognize and differentiate in hex.
  if result < -100:
    # Print negative hex numbers as positive by adding 2^32.
    print('Return code is %08X' % (result + 2**32))
  else:
    print('Return code is %d' % result)
sys.exit(result)
