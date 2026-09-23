from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.books import invoke, library
from app.schemas.library_intelligence import (TriageConfirm, TriageConfirmation, TriageCreate,
                                              TriageEnvelope, TriageList, TriageUpdate)
from app.services.curriculum_triage import canonical_triage_id

router = APIRouter()


def triages(request):
    library(request)
    return request.app.state.curriculum_triage


@router.post('/curriculum-triages', response_model=TriageEnvelope, status_code=201)
async def create_triage(body: TriageCreate, request: Request):
    result = await invoke(triages(request).create, body)
    return JSONResponse(result, status_code=201,
                        headers={'Location': f"/curriculum-triages/{result['session']['id']}"})


@router.get('/curriculum-triages', response_model=TriageList)
async def list_triages(request: Request):
    return await invoke(triages(request).list)


@router.get('/curriculum-triages/{triage_id}', response_model=TriageEnvelope)
async def get_triage(triage_id: str, request: Request):
    return await invoke(triages(request).get, canonical_triage_id(triage_id))


@router.put('/curriculum-triages/{triage_id}', response_model=TriageEnvelope)
async def update_triage(triage_id: str, body: TriageUpdate, request: Request):
    return await invoke(triages(request).update, canonical_triage_id(triage_id), body)


@router.post('/curriculum-triages/{triage_id}/confirm',
             response_model=TriageConfirmation, status_code=201)
async def confirm_triage(triage_id: str, body: TriageConfirm, request: Request):
    result = await invoke(triages(request).confirm, canonical_triage_id(triage_id), body)
    return JSONResponse(result, status_code=201,
                        headers={'Location': f"/learning-goals/{result['goal']['id']}"})
