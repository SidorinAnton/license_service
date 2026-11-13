from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.dependencies.license import get_verified_activation_data
from src.core.database import get_db
from src.schemas.license import ActivationResponse, DeviceDataSchema
from src.services.license import activate_device_service

router = APIRouter(prefix="/client", tags=["Client API"])


@router.post("/activate", response_model=ActivationResponse)
def activate_license(
    device_data: DeviceDataSchema = Depends(get_verified_activation_data),
    db: Session = Depends(get_db),
):
    try:
        result = activate_device_service(db=db, device_data=device_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
