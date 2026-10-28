"""生成可迁移的依赖锁，避免 conda 包元数据中的构建机 file:// 路径。"""
from importlib.metadata import distribution
from packaging.requirements import Requirement
from pathlib import Path

seen = {}
todo = ["rqalpha"]
while todo:
    name = todo.pop()
    d = distribution(name)
    key = d.metadata["Name"].lower()
    if key in seen:
        continue
    seen[key] = d.version
    for spec in d.requires or []:
        r = Requirement(spec)
        if r.marker is None or r.marker.evaluate({"extra": ""}):
            todo.append(r.name)
lines = [n+"=="+v for n, v in sorted(seen.items()) if n != "rqalpha"]
Path(__file__).with_name("requirements-lock.txt").write_text("\n".join(lines)+"\n-e ./rqalpha\n", encoding="utf-8")
print(len(lines), "locked third-party distributions")
