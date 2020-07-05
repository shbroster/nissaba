from typing import Dict, Callable, List, Tuple

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from nissaba.db.schema import BaseType, Base


def noisey_get_one_or_create(session: Session, model: BaseType, **kwargs) -> Base:
    """
    Get an instance of `model` from the database if it exists or create it
    """
    params = _prepare_model_params(session, noisey_get_one_or_create, **kwargs)
    try:
        # Perform and initial query to find the instance
        return session.query(model).filter_by(**params).one()
    except NoResultFound:
        instance = model(**params)
        try:
            # Handle rolling back just this query if the instance has been added
            # before we get change to create it.
            with session.begin_nested():
                session.add(instance)
                return instance
        except IntegrityError:
            return session.query(model).filter_by(**params).one()


def bulk_get_or_create(session: Session, objects: List[Tuple[BaseType, Dict]]):
    instances = []
    with session.begin_nested():
        for model, kwargs in objects:
            instances = _quiet_get_one_or_create(session, model, **kwargs)
    return instances


def quiet_get_one_or_create(session: Session, model: BaseType, **kwargs) -> Base:
    with session.begin_nested():
        return _quiet_get_one_or_create(session, model, **kwargs)


def _quiet_get_one_or_create(session: Session, model: BaseType, **kwargs) -> Base:
    """
    Get an instance of `model` from the database if it exists or create it
    """
    params = _prepare_model_params(session, _quiet_get_one_or_create, **kwargs)
    try:
        # Perform and initial query to find the instance
        return session.query(model).filter_by(**params).one()
    except NoResultFound:
        instance = model(**params)
        session.add(instance)
        return instance


def _prepare_model_params(
    session: Session, get_one_or_create: Callable, **kwargs
) -> Dict:
    my_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, Base):
            value = get_one_or_create(
                session,
                value.__class__,
                **{k: v for k, v in value.__dict__.items() if not k.startswith("_")}
            )
        my_kwargs[key] = value

    return my_kwargs
