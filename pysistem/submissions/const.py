# -*- coding: utf-8 -*-
STATUS_CWAIT = 0 # Waiting for compilation > WAITING...
STATUS_COMPILING = 1 # Compiling           > COMPILING...
STATUS_COMPILEFAIL = 2 # Failed to compile > COMPILATION ERROR
STATUS_WAIT = 3 # Waiting for checking     > WAITING...
STATUS_CHECKING = 4 # Currently checking   > CHECKING...
STATUS_CHECKFAIL = 5 # Failed to check     > INTERNAL ERROR
STATUS_DONE = 6 # Checking finished        > DEPENDS ON RESULT
STATUS_ACT = 7

RESULT_OK = 0
RESULT_TL = 1
RESULT_RE = 2
RESULT_ML = 3
RESULT_IE = 4
RESULT_SV = 5
RESULT_WA = 6
RESULT_PE = 7
RESULT_RJ = 8
RESULT_UNKNOWN = -1

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
    "Rejected"
)