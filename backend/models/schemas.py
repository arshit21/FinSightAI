from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# User and Auth
class UserResponse(BaseModel):
    id: str #UUID from supabase auth
    email: str
    full_name: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# Entity
class EntityBase(BaseModel):
    name: str
    entity_code: Optional[str] = None
    parent_entity_id: Optional[int] = None

class EntityCreate(EntityBase):
    pass

class EntityResponse(EntityBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class EntityTree(EntityResponse):
    children: List ['EntityTree'] = []

# Balance Sheet
class BalanceSheetBase(BaseModel):
    entity_id: int
    fiscal_year: int
    fiscal_year_display: str
    fiscal_period: str
    fiscal_start_date: Optional[str] = None
    fiscal_end_date: Optional[str]

class BalanceSheetCreate(BalanceSheetBase):
    pass

class BalanceSheetResponse(BalanceSheetBase):
    id: int
    uploaded_by: Optional[str]
    uploaded_at: datetime
    source_url: str
    status: str # 'pending', 'processing', 'failed'

    class Config:
        from_attributes = True

class BalanceSheetDetailResponse(BalanceSheetResponse):
    entity_name: str
    raw_gemini: Optional[Dict[str, Any]] = None

# Sheet Items
class SheetItemBase(BaseModel):
    sheet_id: int
    subsidiary_id: Optional[int] = None
    section: str
    line_name: str
    value: Decimal
    attributes: Optional[Dict[str, 'Any']] = None
    item_order: int

class SheetItemCreate(SheetItemBase):
    pass

class SheetItemResponse(SheetItemBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SheetItemGrouped(BaseModel):
    """Group items by section"""
    section: str
    items: List[SheetItemResponse]
    total: Decimal

#File Upload
class BalanceSheetUpload(BaseModel):
    entity_name: str
    entity_code: Optional[str] = None
    fiscal_year: int
    fiscal_year_display: str
    fiscal_period: str
    parent_entity_id: Optional[int] = None

#Gemini Response
class GeminiSubsidiary(BaseModel):
    name: str
    parent: Optional[str] = None

class GeminiLineItem(BaseModel):
    subsidiary: str
    section: str
    line_name: str
    value: float
    currency: Optional[str] = "INR"

class GeminiParsedData(BaseModel):
    entity: Dict[str, Any]
    subsidiaries: List[GeminiSubsidiary]
    line_items: List[GeminiLineItem]

class GeminiProcessingResult(BaseModel):
    success: bool
    data: Optional[GeminiParsedData] = None
    error: Optional[str] = None
    raw: Optional[str] = None

#API Responses
class UploadSuccessResponse(BaseModel):
    message: str
    sheet_id: int
    entity_id: int
    items_count: int

class ErrorResponse(BaseModel):
    detail: str
    status_code: int