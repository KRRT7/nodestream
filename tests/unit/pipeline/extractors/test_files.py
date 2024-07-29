import bz2
import csv
import gzip
import json
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pandas as pd
import pytest
import yaml
from hamcrest import assert_that, equal_to, has_length

from nodestream.pipeline.extractors.files import (
    FileExtractor,
    LocalFileSource,
    RemoteFileExtractor,
)

SIMPLE_RECORD = {"record": "value"}


@pytest.fixture
def fixture_directory():
    with TemporaryDirectory() as tempdir:
        yield tempdir


@pytest.fixture
def json_file(fixture_directory):
    with NamedTemporaryFile(
        "w+", suffix=".json", dir=fixture_directory, delete=False
    ) as temp_file:
        name = temp_file.name
        json.dump(SIMPLE_RECORD, temp_file)
        temp_file.seek(0)
    yield Path(name)


@pytest.fixture
def jsonl_file(fixture_directory):
    with NamedTemporaryFile(
        "w+", suffix=".jsonl", dir=fixture_directory, delete=False
    ) as temp_file:
        name = temp_file.name
        json.dump(SIMPLE_RECORD, temp_file)
        temp_file.write("\n")
        json.dump(SIMPLE_RECORD, temp_file)
        temp_file.seek(0)
    yield Path(name)


@pytest.fixture
def csv_file(fixture_directory):
    with NamedTemporaryFile(
        "w+", suffix=".csv", dir=fixture_directory, delete=False
    ) as temp_file:
        name = temp_file.name
        writer = csv.DictWriter(temp_file, SIMPLE_RECORD.keys())
        writer.writeheader()
        writer.writerow(SIMPLE_RECORD)
        temp_file.seek(0)
    yield Path(name)


@pytest.fixture
def txt_file(fixture_directory):
    with NamedTemporaryFile(
        "w+", suffix=".txt", dir=fixture_directory, delete=False
    ) as temp_file:
        name = temp_file.name
        temp_file.write("hello world")
        temp_file.seek(0)
    yield (path := Path(name))
    path.unlink(missing_ok=True)


@pytest.fixture
def yaml_file(fixture_directory):
    with NamedTemporaryFile(
        "w+", suffix=".yaml", dir=fixture_directory, delete=False
    ) as temp_file:
        name = temp_file.name
        yaml.dump(SIMPLE_RECORD, temp_file)
        temp_file.seek(0)
    yield Path(name)


@pytest.fixture
def parquet_file(fixture_directory):
    with NamedTemporaryFile(
        "w+", suffix=".parquet", dir=fixture_directory, delete=False
    ) as temp_file:
        name = temp_file.name
        df = pd.DataFrame(data=SIMPLE_RECORD, index=[0])
        df.to_parquet(temp_file.name)
        temp_file.seek(0)
    yield Path(name)


@pytest.fixture
def gzip_file(fixture_directory):
    with NamedTemporaryFile(
        "wb", suffix=".json.gz", dir=fixture_directory, delete=False
    ) as temp_file:
        json_data = json.dumps(SIMPLE_RECORD).encode("utf-8")
        with gzip.GzipFile(fileobj=temp_file, mode="wb") as gzip_file:
            gzip_file.write(json_data)
        name = temp_file.name
        if not temp_file.name.endswith(".json.gz"):
            raise Exception("not a json gzip file")
    yield Path(name)


@pytest.fixture
def bz2_file(fixture_directory):
    with NamedTemporaryFile(
        "wb", suffix=".json.bz2", dir=fixture_directory, delete=False
    ) as temp_file:
        json_data = json.dumps(SIMPLE_RECORD).encode("utf-8")
        name = temp_file.name
        with bz2.BZ2File(name, mode="wb") as bz2_file:
            bz2_file.write(json_data)
        if not temp_file.name.endswith(".json.bz2"):
            raise Exception("not a json bz2 file")
    yield Path(name)


@pytest.mark.asyncio
async def test_json_formatting(json_file):
    subject = FileExtractor([LocalFileSource([json_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD]))


@pytest.mark.asyncio
async def test_csv_formatting(csv_file):
    subject = FileExtractor([LocalFileSource([csv_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD]))


@pytest.mark.asyncio
async def test_txt_formatting(txt_file):
    subject = FileExtractor([LocalFileSource([txt_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([{"line": "hello world"}]))


@pytest.mark.asyncio
async def test_jsonl_formatting(jsonl_file):
    subject = FileExtractor([LocalFileSource([jsonl_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD, SIMPLE_RECORD]))


@pytest.mark.asyncio
async def test_yaml_formatting(yaml_file):
    subject = FileExtractor([LocalFileSource([yaml_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD]))


@pytest.mark.asyncio
async def test_parquet_formatting(parquet_file):
    subject = FileExtractor([LocalFileSource([parquet_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD]))


@pytest.mark.asyncio
async def test_gzip_formatting(gzip_file):
    subject = FileExtractor([LocalFileSource([gzip_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD]))


@pytest.mark.asyncio
async def test_bz2_formatting(bz2_file):
    subject = FileExtractor([LocalFileSource([bz2_file])])
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD]))


def test_declarative_init(
    fixture_directory, csv_file, json_file, txt_file, jsonl_file, yaml_file
):
    subject = FileExtractor.from_file_data(globs=[f"{fixture_directory}/**"])
    assert_that(list(subject.file_sources[0].paths), has_length(5))


@pytest.mark.asyncio
async def test_remote_file_extractor_extract_records(mocker, httpx_mock):
    files = ["https://example.com/file.json", "https://example.com/file2.json"]
    for file in files:
        httpx_mock.add_response(
            url=file,
            method="GET",
            json=SIMPLE_RECORD,
        )
    subject = RemoteFileExtractor.from_file_data(urls=files)
    results = [r async for r in subject.extract_records()]
    assert_that(results, equal_to([SIMPLE_RECORD, SIMPLE_RECORD]))
