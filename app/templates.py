from fastapi.templating import Jinja2Templates

from app.utils.timezone import (
    format_compact,
    format_date,
    format_full,
    format_table,
    format_vn,
    is_stale_sync,
    relative_time,
)

templates = Jinja2Templates(directory="templates")

templates.env.filters["vn_time"] = lambda dt: format_vn(dt)
templates.env.filters["vn_date"] = lambda dt: format_date(dt)
templates.env.filters["vn_full"] = lambda dt: format_full(dt)
templates.env.filters["vn_table"] = lambda dt: format_table(dt)
templates.env.filters["vn_compact"] = lambda dt: format_compact(dt)
templates.env.filters["relative_time"] = lambda dt: relative_time(dt)
templates.env.filters["is_stale_sync"] = is_stale_sync
