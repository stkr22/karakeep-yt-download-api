"""Payload of Karakeep's outgoing webhook."""

from pydantic import BaseModel, ConfigDict, Field


class KarakeepWebhook(BaseModel):
    """Subset of the Karakeep webhook body this service cares about."""

    model_config = ConfigDict(extra="ignore")

    job_id: str | None = Field(default=None, alias="jobId")
    bookmark_id: str | None = Field(default=None, alias="bookmarkId")
    user_id: str | None = Field(default=None, alias="userId")
    operation: str | None = None
    type: str | None = None
    url: str | None = None
