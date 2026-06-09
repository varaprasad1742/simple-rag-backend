from app.observability.decorators import (
    observe
)


class QueryTransformer:

    @classmethod
    @observe("query_transform")
    async def transform(
        cls,
        query: str
    ):

        query = query.strip()

        return query