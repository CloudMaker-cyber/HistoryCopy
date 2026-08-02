"""保留期限清理:删除超过保留天数且未置顶的记录(含对应图片文件)。"""

import datetime

from storage import Storage


def cleanup_expired(storage: Storage, retention_days: int) -> int:
    """清理过期记录,返回删除条数。置顶记录不受影响。"""
    if retention_days <= 0:
        return 0
    cutoff = (datetime.datetime.now()
              - datetime.timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
    expired = storage.list_expired(cutoff)
    for item in expired:
        storage.delete(item["id"])
    return len(expired)
