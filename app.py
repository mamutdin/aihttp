import asyncio
import datetime
import json
from typing import Type, Callable, Awaitable
from aiohttp import web, ClientSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from config import PG_DSN
from models import Base, People

engine = create_async_engine(PG_DSN)
Session = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@web.middleware
async def session_middleware(request: web.Request, handler: Callable[[web.Request], Awaitable[web.Response]]):
    async with Session() as session:
        request["session"] = session
        return await handler(request)


async def get_item(url, d: dict, key1, key2, session):
    async with session.get(url) as response:
        json_data = await response.json()
        name = json_data[key1]
        d[key2] = name


async def get_items(urls: list, d: dict, key1, key2, session):
    l = []
    for url in urls:
        async with session.get(url) as response:
            json_data = await response.json()
            l.append(json_data[key1])
    l = ', '.join(l)
    d[key2] = l


async def get_person(person_id: int, session: Session):
    async with session.get(f'https://swapi.dev/api/people/{person_id}') as response:
        json_data = await response.json()
        json_data['ID'] = person_id

        if 'detail' not in json_data:
            result2 = {key: val for key, val in json_data.items() if
                       key != 'created' and key != 'edited' and key != 'url'}
            coro1 = get_item(json_data['homeworld'], result2, 'name', 'homeworld', session)
            coro2 = get_items(json_data['films'], result2, 'title', 'films', session)
            coro3 = get_items(json_data['species'], result2, 'name', 'species', session)
            coro4 = get_items(json_data['starships'], result2, 'name', 'starships', session)
            coro5 = get_items(json_data['vehicles'], result2, 'name', 'vehicles', session)
            res = await asyncio.gather(coro1, coro2, coro3, coro4, coro5)
        return result2


def raise_http_error(error_class, message: str | dict):
    raise error_class(
        text=json.dumps({"status": "error", "description": message}),
        content_type="application/json",
    )


async def get_orm_item(orm_class, object_id, session):
    item = await session.get(orm_class, object_id)
    if item is None:
        raise raise_http_error(web.HTTPNotFound, f'{orm_class.__name__} not found')


class UserView(web.View):

    async def get(self):
        user_id = int(self.request.match_info["user_id"])
        user = await get_orm_item(People, user_id, self.request["session"])
        return web.json_response({"id": user.id, 'name': user.json})

    async def post(self):
        user_data = await self.request.json()
        person_id = user_data['ID']
        person = get_person(person_id, self.request['session'])
        new_user = People(person)
        self.request['session'].add(new_user)
        await self.request['session'].commit()
        return web.json_response({"id": new_user.id})

    async def patch(self):
        user_id = int(self.request.match_info["user_id"])
        user_data = await self.request.json()
        user = await get_orm_item(People, user_id, self.request["session"])
        for field, value in user_data.items():
            setattr(user, field, value)
        self.request["session"].add(user)
        await self.request["session"].commit()
        return web.json_response({"status": "success"})

    async def delete(self):
        user_id = int(self.request.match_info["user_id"])
        user = await get_orm_item(People, user_id, self.request["session"])
        await self.request["session"].delete(user)
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
    web.post('/users', UserView),
    web.get('/users/{user_id:\d+}', UserView)
])

if __name__ == '__main__':
    web.run_app(app)
