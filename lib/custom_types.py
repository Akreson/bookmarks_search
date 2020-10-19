import multiprocessing
from typing import Set, List, Tuple, TypeVar

Context = multiprocessing.context.BaseContext
Queue = multiprocessing.Queue
MatchingResult = List[Tuple[int, int]]
WorkerJobData = Tuple[int, int, int, List[str], List[str]]
WorkerTaskResult = Tuple[int, MatchingResult]

JSONVar = TypeVar("JsonVar", str, int, float)