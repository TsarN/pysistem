# -*- coding: utf-8 -*-
STATUS_CWAIT = 0 # Waiting for compilation > WAITING...
STATUS_COMPILING = 1 # Compiling           > COMPILING...
STATUS_COMPILEFAIL = 2 # Failed to compile > COMPILATION ERROR
STATUS_WAIT = 3 # Waiting for checking     > WAITING...
STATUS_CHECKING = 4 # Currently checking   > CHECKING...
STATUS_CHECKFAIL = 5 # Failed to check     > INTERNAL ERROR
STATUS_DONE = 6 # Checking finished        > DEPENDS ON RESULT
STATUS_ACT = 7 # Checker is active         > ACT

RESULT_OK = 0 # Everything went fine
RESULT_TL = 1 # Time limit occurred
RESULT_RE = 2 # Runtime error occurred
RESULT_ML = 3 # Memory limit occurred
RESULT_IE = 4 # Internal error occurred
RESULT_SV = 5 # Security violation occurred
RESULT_WA = 6 # Wrong answer
RESULT_PE = 7 # Presentation error
RESULT_RJ = 8 # Rejected
RESULT_UNKNOWN = -1 # Not tested

STR_STATUS = (
    "Waiting...",
    "Compiling...",
    "Compilation Error",
    "Waiting...",
    "Checking...",
    "Internal Error..."
)

STR_RESULT = (
    "Accepted",
    "Time Limit",
    "Runtime Error",
    "Memory Limit",
    "Internal Error",
    "Security Violation",
    "Wrong Answer",
    "Presentation Error",
    "Rejected",
    # Insert other results here
    "Not tested"
)