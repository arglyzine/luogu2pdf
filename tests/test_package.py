"""打包脚本（package.sh）生成测试。"""

from main import write_package_script
from model import Contest
from pathlib import Path


def test_write_package_script(tmp_path):
    contest = Contest(name="2026-08-05 模拟赛")
    write_package_script(tmp_path, contest)
    sh = (tmp_path / "package.sh").read_text()
    assert 'name = "2026-08-05-模拟赛-下发"' in sh
    assert "tex/build.sh" in sh
    assert "第*.pdf" in sh
    assert "data" in sh
    assert (tmp_path / "package.sh").stat().st_mode & 0o111  # 可执行


def test_write_package_script_no_spaces_in_zip_name(tmp_path):
    contest = Contest(name="NOIP 模拟赛")
    write_package_script(tmp_path, contest)
    sh = (tmp_path / "package.sh").read_text()
    assert 'name = "NOIP-模拟赛-下发"' in sh
