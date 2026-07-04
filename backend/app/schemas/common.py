from typing import Any

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class AppSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )


class PageData(AppSchema):
    items: list[Any]
    page: int
    page_size: int
    total: int


def dump_data(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(by_alias=True)
    if isinstance(data, list):
        return [dump_data(item) for item in data]
    if isinstance(data, dict):
        return {to_camel(key): dump_data(value) for key, value in data.items()}
    return data


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": dump_data(data)}
