from typing import TypeVar, Type
from enum import Enum, auto

from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy_utils import ChoiceType

Base = declarative_base()
_B = TypeVar("B", bound=Base)
BaseType = Type[_B]


class Outcome(Enum):
    PASS = 0
    SKIP = 1
    ERROR = 2
    FAIL = 3
    XPASS = 4
    XFAIL = 5


class TestSpec(Base):
    __tablename__ = "test_spec"
    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False, doc="The name of the test")
    vut = Column(String, nullable=False, doc="The version of the software under test")
    parameters = Column(HSTORE, nullable=False, doc="Parameters passed to the test")

    os_id = Column(
        Integer,
        ForeignKey("operating_system.id"),
        nullable=False,
        doc="The OS where the test is being executed.",
    )
    os = relationship("OperatingSystem")

    hardware_id = Column(
        Integer,
        ForeignKey("hardware.id"),
        nullable=False,
        doc="The hardware of the machine where the test is being exectured",
    )
    hardware = relationship("Hardware")

    __table_args__ = (UniqueConstraint(name, vut, parameters, os_id, hardware_id),)

    def __repr__(self):
        return (
            f"TestSpec({self.name}, {self.vut}, {self.os}, {self.hardware}, "
            f"{self.parameters}"
        )


class OperatingSystem(Base):
    __tablename__ = "operating_system"
    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False, doc="The name of the OS, e.g. Ubuntu")
    type = Column(
        String,
        nullable=False,
        doc="A higher level categorisation of the OS, e.g. Linux",
    )
    version = Column(String, nullable=False, doc="The version of the OS, e.g. 18.04")

    __table_args__ = (UniqueConstraint(name, type, version),)

    def __repr__(self):
        return f"OS({self.name}, {self.type}, {self.version})"


class Hardware(Base):
    __tablename__ = "hardware"
    id = Column(Integer, primary_key=True)

    architecture = Column(
        String, nullable=False, doc="The CPU architecture, e.g. x86, ARM"
    )
    microarchitecture = Column(
        String, nullable=False, doc="The CPU microachitecture, e.g. Haswell, Skylake"
    )
    size = Column(String, nullable=False, doc="The size of the machine being used")

    __table_args__ = (UniqueConstraint(architecture, microarchitecture, size),)

    def __repr__(self):
        return f"Hardware({self.size}, {self.architecture}, {self.microarchitecture})"


class TestRun(Base):
    __tablename__ = "test_run"
    id = Column(Integer, primary_key=True)

    runner = Column(
        String, nullable=False, doc="What was responsible for running this test"
    )
    branch = Column(String, nullable=False, doc="The name of the branch being tested")
    start_datetime = Column(
        DateTime, nullable=False, doc="When the test run was started"
    )
    milliseconds_duration = Column(
        Integer, nullable=False, doc="The duration of the test run in milliseconds"
    )

    __table_args__ = (
        UniqueConstraint(runner, branch, start_datetime, milliseconds_duration),
    )

    def __repr__(self):
        return f"TestRun({self.runner}, {self.branch})"


class TestResult(Base):
    __tablename__ = "test_result"
    id = Column(Integer, primary_key=True)

    outcome = Column(
        ChoiceType(Outcome, impl=Integer()),
        nullable=False,
        doc="The test outcome (as an integer)",
    )
    start_datetime = Column(DateTime, nullable=False, doc="When the test was started")
    milliseconds_duration = Column(
        Integer, doc="The duration of the test in milliseconds"
    )

    exception_id = Column(
        Integer, ForeignKey("exception.id"), doc="An exception raised by the test"
    )
    exception = relationship("TestException")

    run_id = Column(
        Integer,
        ForeignKey("test_run.id"),
        nullable=False,
        doc="The runner responsible for running the test",
    )
    run = relationship("TestRun")

    test_spec_id = Column(
        Integer,
        ForeignKey("test_spec.id"),
        nullable=False,
        doc="What was the test that was run",
    )
    test_spec = relationship("TestSpec")

    __table_args__ = (UniqueConstraint(outcome, start_datetime, run_id, test_spec_id),)

    def __repr__(self):
        return f"TestResult({self.outcome}, {self.test_spec})"


class TestException(Base):
    __tablename__ = "exception"
    id = Column(Integer, primary_key=True)

    message = Column(String, nullable=False, doc="The exception message")
    class_name = Column(String, nullable=False, doc="The type of the exception")
    filename = Column(
        String, nullable=False, doc="The file where the exception was hit"
    )
    line_no = Column(
        Integer, nullable=False, doc="The line number on which the exception was hit"
    )

    __table_args__ = (UniqueConstraint(message, class_name, filename, line_no),)

    def __repr__(self):
        return f"{self.class_name.capitalize()}({self.message})"


TABLES = []
