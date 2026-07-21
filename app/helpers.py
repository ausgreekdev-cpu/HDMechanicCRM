from math import ceil


def paginate(query, page, per_page=50):
    page = max(1, page)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, ceil(total / per_page))
    return {
        "rows": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }
