import asyncio
import random
import logging
from typing import Callable, Any, Tuple, Type, Tuple as TypeTuple

logger = logging.getLogger("jevflow.retry")


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 2,
    base_delay_ms: float = 50.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: TypeTuple[Type[Exception], ...] = (Exception,),
    *args,
    **kwargs,
) -> Tuple[Any, int]:
    """
    Execute an async function with exponential backoff and random jitter.
    
    Returns:
        Tuple of (result, retries_attempted: int)
        
    Raises:
        The last encountered exception if all retries are exhausted.
    """
    retries = 0
    last_exception = None

    while retries <= max_retries:
        try:
            result = await func(*args, **kwargs)
            return result, retries
        except retryable_exceptions as exc:
            last_exception = exc
            retries += 1
            if retries > max_retries:
                logger.warning(
                    "All %d retry attempts exhausted for %s: %s",
                    max_retries,
                    getattr(func, "__name__", "callable"),
                    exc,
                )
                break

            # Exponential backoff with 20% random jitter
            delay = (base_delay_ms / 1000.0) * (backoff_factor ** (retries - 1))
            jitter = delay * random.uniform(0.0, 0.2)
            sleep_sec = delay + jitter

            logger.info(
                "Retry %d/%d for %s after %.3fs due to: %s",
                retries,
                max_retries,
                getattr(func, "__name__", "callable"),
                sleep_sec,
                exc,
            )
            await asyncio.sleep(sleep_sec)

    raise last_exception
