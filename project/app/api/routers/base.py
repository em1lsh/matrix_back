from fastapi import APIRouter


base_router = APIRouter(tags=["Base"], include_in_schema=False)

# @base_router.get('/media/{file}')
# async def get_media(
#     file: str
# ):
#     my_file = Path(f'./media/{file}')

#     if not my_file.exists():
#         raise HTTPException(
#             status_code=http.HTTPStatus.NOT_FOUND,
#             detail="File not found."
#         )

#     return FileResponse(
#         path=f'./media/{file}',
#         filename=file
#     )
