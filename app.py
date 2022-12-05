import json
from typing import Callable, Awaitable
from aiohttp import web
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.config import PG_DSN
from models import Base, People

engine = create_async_engine(PG_DSN)
Session = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@web.middleware
async def session_middleware(request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]):
    async with Session() as session:
        request["session"] = session
        return await handler(request)


def raise_http_error(error_class, message: str | dict):
    raise error_class(
        text=json.dumps({"status": "error", "description": message}),
        content_type="application/json",
    )


async def get_orm_item( orm_class, object_id, session):
    item = await session.get(orm_class, object_id)
    if item is None:
        raise raise_http_error(web.HTTPNotFound, f'{orm_class.__name__} not found')


class UserView(web.View):

    async def get(self):
        person_id = int(self.request.match_info["person_id"])
        # person = await get_orm_item(People, person_id, self.request["session"])
        person = await self.request["session"].get(People, person_id)
        if person is None:
            raise raise_http_error(web.HTTPNotFound, f'{People.__name__} not found')
        return web.json_response({'id': person.id, 'json': person.json})

    async def post(self):
        person_data = await self.request.json()
        new_person = People(**person_data)
        self.request["session"].add(new_person)
        await self.request["session"].commit()
        return web.json_response({"id": new_person.id})

    async def patch(self):
        person_id = int(self.request.match_info["person_id"])
        person_data = await self.request.json()
        # person = await get_orm_item(People, person_id, self.request["session"])
        person = await self.request["session"].get(People, person_id)
        if person is None:
            raise raise_http_error(web.HTTPNotFound, f'{People.__name__} not found')
        for field, value in person_data.items():
            setattr(person, field, value)
        self.request["session"].add(person)
        await self.request["session"].commit()
        return web.json_response({"status": "success"})

    async def delete(self):
        person_id = int(self.request.match_info["person_id"])
        # user = await get_orm_item(People, person_id, self.request["session"])
        person = await self.request["session"].get(People, person_id)
        if person is None:
            raise raise_http_error(web.HTTPNotFound, f'{People.__name__} not found')
        await self.request["session"].delete(person)
        await self.request["session"].commit()
        return web.json_response({"status": "success"})


async def app_context(app: web.Application):
    print("START")
    async with engine.begin() as conn:
        async with Session() as session:
            await session.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            await session.commit()
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    print("FINISH")


app = web.Application(middlewares=[session_middleware])
app.cleanup_ctx.append(app_context)

app.add_routes([
    web.post('/people/', UserView),
    web.get('/people/{person_id:\d+}', UserView),
    web.delete('/people/{person_id:\d+}', UserView),
    web.patch('/people/{person_id:\d+}', UserView)
])

if __name__ == '__main__':
    web.run_app(app)
