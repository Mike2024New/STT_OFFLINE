from app.stt import STT_INFO
from fastapi import APIRouter

router = APIRouter(
    prefix='/stt',
    tags=['stt'],
)


@router.get('/info/')
def test():
    return {'info': STT_INFO}
