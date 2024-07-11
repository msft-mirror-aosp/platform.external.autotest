# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
from typing import Optional, List
from autotest_lib.client.common_lib import error


class Bound(object):
    """
    Bound class does bounds checking for a scalar metrics from a test.
    """

    def __init__(self,
                 scalarNameRegex: str,
                 min: Optional[float] = None,
                 max: Optional[float] = None) -> None:
        self.scalarRE = re.compile(scalarNameRegex)
        self.min = min
        self.max = max

    def eval_scalar(self, name: str, val: float) -> Optional[int]:
        """eval_scalar evaluates the scalar against the bound

        returns: -1 if value is less than min bound,
        1 if bound is greater than max bound,
        0 if value is within bounds.
        None if the scalar name does not match the regex.
        """
        if not self.scalarRE.match(name):
            return None
        if self.min is not None and val < self.min:
            return -1
        if self.max is not None and val > self.max:
            return 1
        return 0

    def __repr__(self) -> str:
        return f'Bound(scalarNameRegex={self.scalarRE}, min={self.min}, max={self.max})'

    def __hash__(self) -> int:
        return hash(repr(self))


def evaluate_test_bounds(testScalars: dict, bounds: List[Bound]) -> None:
    """evaluate_test_bounds evaluates the test scalars against all bounds

    raises an error.TestFail exception if any of the bounds fail or do not
    have a matching scalar.
    """
    if bounds is None or len(bounds) == 0:
        logging.info('No bounds specified, skipping bounds evaluation')
        return
    boundEvaluated = {}
    errors = []
    for name, val in testScalars.items():
        try:
            val = float(val)
        except ValueError:
            logging.warning(f'skipping non-float metric value {name} = {val}')
            continue
        for bound in bounds:
            result = bound.eval_scalar(name, val)
            if result is None:
                continue
            elif result < 0:
                errors.append(
                        f'metric {name}: measured value {val} < lower bound {bound.min}'
                )
            elif result > 0:
                errors.append(
                        f'metric {name}: measured value {val} > upper bound {bound.max}'
                )
            elif result == 0:
                logging.info(
                        f'metric {name}: meaured value {val} is within range [{bound.min}, {bound.max}]'
                )
            boundEvaluated[bound] = True

    for bound in bounds:
        if bound not in boundEvaluated:
            errors.append(
                    f'no metric found matching pattern {bound.scalarRE.pattern}'
            )

    if errors:
        raise error.TestFail(
                f'Failed bounds check with {len(errors)} errors: {", ".join(errors)}'
        )

    logging.info(
            f'Bounds check passed evaluating {len(testScalars)} against {len(bounds)} bounds'
    )
