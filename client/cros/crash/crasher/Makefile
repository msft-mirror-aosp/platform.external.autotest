# Copyright 2010 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

BINS = crasher_nobreakpad
SRC = crasher.cc
OBJS = crasher.o bomb.o
# Use a non-standard extension to avoid the AUTOTEST_MASK that intends to
# remove these since they're usually large and redundant.
TGZ = crasher.tgz-unmasked

all: $(TGZ)

# gzip so that portage does not strip.
$(TGZ): $(BINS)
	tar czf $(TGZ) $^
	rm -f $(BINS)

crasher_nobreakpad: $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

.cc.o:
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	$(RM) *.o $(BIN) $(TGZ)
