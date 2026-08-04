"""打包脚本（package.sh）生成测试。"""

from main import write_package_script
from model import Contest
from pathlib import Path


def test_write_package_script(tmp_path):
    contest = Contest(name="2026-08-05 模拟赛")
    write_package_script(tmp_path, contest)
    sh = (tmp_path / "package.sh").read_text()
    assert "create_distribution_zip" in sh
    assert "tex/build.sh" in sh
    assert (tmp_path / "package.sh").stat().st_mode & 0o111  # 可执行


def test_write_package_script_no_spaces_in_zip_name(tmp_path):
    contest = Contest(name="NOIP 模拟赛")
    write_package_script(tmp_path, contest)
    sh = (tmp_path / "package.sh").read_text()
    assert "Contest(name='NOIP 模拟赛')" in sh


def test_create_distribution_zip(tmp_path):
    from main import create_distribution_zip
    contest = Contest(name="测试赛")
    (tmp_path / "第1题-a.pdf").write_bytes(b"%PDF-1")
    (tmp_path / "测试赛-题面合集.pdf").write_bytes(b"%PDF-1")
    (tmp_path / "data" / "t1").mkdir(parents=True)
    (tmp_path / "data" / "t1" / "1.in").write_text("1\n")
    out = create_distribution_zip(tmp_path, contest)
    assert out.name == "测试赛-下发.zip"
    import zipfile
    names = zipfile.ZipFile(out).namelist()
    assert "第1题-a.pdf" in names
    assert "测试赛-题面合集.pdf" in names
    assert "data/t1/1.in" in names
