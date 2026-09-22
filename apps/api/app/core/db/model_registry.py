"""Imports every model module for its side effect of registering tables
on `Base.metadata`. Alembic's `env.py` imports this module (not each model
module individually) so autogenerate always sees the full schema — a new
domain module added in a later phase registers itself here in one place,
rather than every future migration needing to remember every module.
"""

from app.geography import models as geography_models  # noqa: F401
from app.institutions import models as institutions_models  # noqa: F401
from app.jobs import models as jobs_models  # noqa: F401
from app.search import models as search_models  # noqa: F401
from app.services import models as services_models  # noqa: F401
from app.sources import models as sources_models  # noqa: F401
from app.users import models as users_models  # noqa: F401
