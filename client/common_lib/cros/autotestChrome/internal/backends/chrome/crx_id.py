# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Read a CRX file and write out the App ID and the Full Hash of the ID.
See: http://code.google.com/chrome/extensions/crx.html
and 'http://stackoverflow.com/questions/'
  + '1882981/google-chrome-alphanumeric-hashes-to-identify-extensions'
for docs on the format.
"""

from __future__ import division
from __future__ import absolute_import
import base64
import os
import hashlib
import json
# pylint: disable=redefined-builtin
from io import open
import struct
import six

if six.PY3:
  def ord(x):
    return x

  def chr(x):
    return bytes([x])

EXPECTED_CRX_MAGIC_NUM = b'Cr24'
EXPECTED_CRX_VERSION = 2

def HexToMPDecimal(hex_chars):
  """ Convert bytes to an MPDecimal string. Example \x00 -> "aa"
      This gives us the AppID for a chrome extension.
  """
  result = b''
  base = ord(b'a'[0])
  for hex_char in hex_chars:
    value = ord(hex_char)
    dig1 = value // 16
    dig2 = value % 16
    result += chr(dig1 + base)
    result += chr(dig2 + base)
  return result.decode('utf-8')

def GetPublicKeyUnpacked(f, filepath):
  manifest = json.load(f)
  if 'key' not in manifest:
    # Use the path as the public key.
    # See Extension::GenerateIdForPath in extension.cc
    return GetPublicKeyFromPath(filepath)
  else:
    return base64.standard_b64decode(manifest['key'])

def HasPublicKey(filename):
  if os.path.isdir(filename):
    with open(os.path.join(filename, 'manifest.json'), 'rb') as f:
      manifest = json.load(f)
      return 'key' in manifest
  return False

def GetPublicKey(filename, from_file_path, is_win_path=False):
  if from_file_path:
    return GetPublicKeyFromPath(
        filename, is_win_path=is_win_path)

  pub_key = ''
  if os.path.isdir(filename):
    # Assume it's an unpacked extension
    f = open(os.path.join(filename, 'manifest.json'), 'rb')
    pub_key = GetPublicKeyUnpacked(f, filename)
    f.close()
  else:
    # Assume it's a packed extension.
    f = open(filename, 'rb')
    pub_key = GetPublicKeyPacked(f)
    f.close()
  return pub_key

def GetCRXAppID(filename, from_file_path=False, is_win_path=False):
  pub_key = GetPublicKey(filename, from_file_path, is_win_path=is_win_path)
  pub_key_hash = hashlib.sha256(pub_key).digest()
  # AppID is the MPDecimal of only the first 128 bits of the hash.
  return HexToMPDecimal(pub_key_hash[:128//8])
