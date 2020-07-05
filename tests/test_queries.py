from datetime import datetime

import random
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.event import listen

from nissaba.db.queries import noisey_get_one_or_create, quiet_get_one_or_create, bulk_get_or_create
from nissaba.db import schema as sch


class DBStatementCounter(object):
    """
    Use as a context manager to count the number of execute()'s performed
    against the given sqlalchemy connection.

    Usage:
        with DBStatementCounter(conn) as ctr:
            conn.execute("SELECT 1")
            conn.execute("SELECT 1")
        assert ctr.get_count() == 2
    """
    def __init__(self, conn):
        self.conn = conn
        self.count = 0
        # Will have to rely on this since sqlalchemy 0.8 does not support
        # removing event listeners
        self.do_count = False
        listen(conn, 'after_execute', self.callback)

    def __enter__(self):
        self.do_count = True
        return self

    def __exit__(self, *_):
        self.do_count = False

    def get_count(self):
        return self.count

    def callback(self, *_):
        if self.do_count:
            self.count += 1


def os_kwargs():
    return {
        "name": random.choice(
            ["ubuntu", "sles", "redhat", "centos", "debian", "gentoo"]
        ),
        "type": "Linux",
        "version": f"{random.randint(0,20)}.{random.randint(0,20)}.{random.randint(0,20)}",
    }


def hardware_kwargs():
    return {
        "architecture": random.choice(["x86", "x32", "arm"]),
        "microarchitecture": random.choice(
            [
                "haswell",
                "broadwell",
                "skylake",
                "coffee lake",
                "cascade lake",
                "comet lake",
            ]
        ),
        "size": random.choice(["small", "medium", "large", "2xlarge", "4xlarge"]),
    }


def exception_kwargs():
    return {
        "message": random.choice(
            ["There was an error", "Something broke", "Don't do that"]
        ),
        "class_name": random.choice(
            ["Exception", "Assertion", "TypeError", "ValueError"]
        ),
        "filename": "test.py",
        "line_no": random.randint(0, 10),
    }


def test_run_kwags():
    return {
        "runner": random.choice(["overnight", "push", "PR", "regular"]),
        "branch": "master",
        "start_datetime": datetime.now(),
        "milliseconds_duration": random.randint(10000, 12000),
    }


def test_spec_kwargs(os=None, hardware=None):
    os = os if os else sch.OperatingSystem(**os_kwargs())
    hardware = hardware if hardware else sch.Hardware(**hardware_kwargs())
    return {
        "name": f"Test Number {random.randint(0, 1000)}",
        "vut": random.choice(["1.2.1", "1.2.2", "2.0.0"]),
        "parameters": {"a": "the", "b": "big", "abcdefg": "red"},
        "os": os,
        "hardware": hardware,
    }


def test_result_kwargs(run=None, spec=None):
    run = run if run else sch.TestRun(**test_run_kwags())
    spec = spec if spec else sch.TestSpec(**test_spec_kwargs())
    return {
        "outcome": random.choice([o for o in sch.Outcome]),
        "start_datetime": datetime.now(),
        "milliseconds_duration": random.randint(10, 100),
        "run": run,
        "test_spec": spec,
    }


@pytest.mark.parametrize(
    "num_calls,model,kwargs,func,num_queries",
    (
        [
            (1, sch.OperatingSystem, os_kwargs(), quiet_get_one_or_create, 4),
            (5, sch.OperatingSystem, os_kwargs(), quiet_get_one_or_create, 16),
            (3, sch.Hardware, hardware_kwargs(), quiet_get_one_or_create, 10),
            (3, sch.TestException, exception_kwargs(), quiet_get_one_or_create, 10),
            (3, sch.TestSpec, test_spec_kwargs(), quiet_get_one_or_create, 18),
            (3, sch.TestResult, test_result_kwargs(), quiet_get_one_or_create, 26),
            (3, sch.TestRun, test_run_kwags(), quiet_get_one_or_create, 10),
            (1, sch.OperatingSystem, os_kwargs(), noisey_get_one_or_create, 4),
            (5, sch.OperatingSystem, os_kwargs(), noisey_get_one_or_create, 8),
            (3, sch.Hardware, hardware_kwargs(), noisey_get_one_or_create, 6),
            (3, sch.TestException, exception_kwargs(), noisey_get_one_or_create, 6),
            (3, sch.TestSpec, test_spec_kwargs(), noisey_get_one_or_create, 18),
            (3, sch.TestResult, test_result_kwargs(), noisey_get_one_or_create, 30),
            (3, sch.TestRun, test_run_kwags(), noisey_get_one_or_create, 6),
        ]
    ),
)
def test_get_one_or_create(
    postgres_session: Session, num_calls, model, kwargs, func, num_queries
) -> None:
    """Test that the database can get or create objects without any resulting duplicates"""
    oses = postgres_session.query(model).all()
    assert len(oses) == 0

    with DBStatementCounter(postgres_session.connection()) as ctr:
        instances = [
            func(postgres_session, model, **kwargs) for _ in range(num_calls)
        ]
        assert ctr.get_count() == num_queries

    entries = postgres_session.query(model).all()
    assert len(entries) == 1

    for instance in instances:
        for key, value in kwargs.items():
            if not isinstance(value, sch.Base):
                assert getattr(instance, key) == value

        assert entries[0] == instance


@pytest.mark.parametrize(
    "func,num_objects,num_insertions,test_run,num_queries,num_entries",
    (
        [
            (bulk_get_or_create, 100, 100, None, 810, 66),
            (quiet_get_one_or_create, 100, 100, None, 1008, 66),
            (noisey_get_one_or_create, 100, 100, None, 1424, 66),
            (bulk_get_or_create, 100, 100, sch.TestRun(**test_run_kwags()), 749, 67),
            (quiet_get_one_or_create, 100, 100, sch.TestRun(**test_run_kwags()), 947, 67),
            (noisey_get_one_or_create, 100, 100, sch.TestRun(**test_run_kwags()), 1241, 67),
        ]
    ),
)
def test_large_create_with_dupes(
    postgres_session: Session, func, num_objects, num_insertions, test_run, num_queries, num_entries
):
    random.seed(0)
    test_results = [test_result_kwargs(run=test_run) for _ in range(num_objects)]
    with DBStatementCounter(postgres_session.connection()) as ctr:
        if func == bulk_get_or_create:
            objs = [(sch.TestResult, random.choice(test_results)) for _ in range(num_insertions)]
            bulk_get_or_create(postgres_session, objs)
        else:
            for _ in range(num_insertions):
                func(
                    postgres_session,
                    sch.TestResult,
                    **random.choice(test_results),
                )
        assert ctr.get_count() == num_queries
    assert len(postgres_session.query(sch.TestResult).all()) == num_entries