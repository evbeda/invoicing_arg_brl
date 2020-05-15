from datetime import datetime, timedelta
from timeit import default_timer
import time


class CircuitBreaker(object):
    TIMEOUT = 9
    THRESHOLD = 5
    CLOSED = 0
    HALF_OPEN = 1
    OPEN = 2
    DEFAULT_EXCEPTION = Exception

    def __init__(self, threshold=None, timeout=None, exception=None, external_service=None):
        self._threshold = threshold - 1 if threshold else self.THRESHOLD
        self._timeout = timeout if timeout else self.TIMEOUT
        self._exception = exception if exception else self.DEFAULT_EXCEPTION
        self._failure_count = 0
        self._last_failure = None
        self._state = self.CLOSED
        self._external_service = external_service

    def __update_circuit_state(self):
        if self._state is self.CLOSED:
            if self._failure_count >= self._threshold:
                self._state = self.OPEN

        elif self._state is self.HALF_OPEN:
            if self._failure_count == 1:
                self._state = self.OPEN
            else:
                self.__reset_to_default()

        else:
            if self._last_failure \
                    and default_timer() - self._last_failure > self._timeout \
                    and self._failure_count >= self._threshold:
                self._state = self.HALF_OPEN

    def call_external_service(self, *args, **kwargs):
        self.__update_circuit_state()
        call = None
        if self._state in (self.CLOSED, self.HALF_OPEN):
            try:
                call = self._external_service(*args, **kwargs)
            except self._exception:
                self.__service_failure()
                return
        else:
            return None

        return call

    def __service_failure(self):
        if self._state is self.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self._threshold:
                self._last_failure = default_timer()

        elif self._state is self.HALF_OPEN:
            self._failure_count = 1
            self._last_failure = default_timer()

    def __reset_to_default(self):
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure = None

    @property
    def show_state(self):
        if self._state == 0:
            return "CLOSED"
        elif self._state == 1:
            return "HALF-OPEN"
        else:
            return "OPEN"

    def __str__(self):
        return '''
        Circuit Breaker info:
        -Function registered: {},
        -Time since last failure: {}s,
        -Circuit state: {},
        -Circuit timeout: {}s,
        -Circuit threshold: {},
        -Expected exception: {}  
        '''.format(self._external_service.__name__.capitalize(),
                   0 if not self._last_failure else self._last_failure,
                   self.show_state,
                   self._timeout,
                   self._threshold + 1,
                   self._exception.__name__
                   )