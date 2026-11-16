import io


def test_home_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Screen Resumes" in res.data


def test_upload_and_results(client):
    data = {
        "job_title": "Flask Developer",
        "job_description": "Need Python, Flask, SQL and Git. 1 year experience.",
        "resumes": [
            (io.BytesIO(b"Meera Iyer\nPython Flask SQL Git, 2 years"), "meera.txt"),
            (io.BytesIO(b"Kabir Singh\nPhotoshop and video editing"), "kabir.txt"),
            (io.BytesIO(b"\x89PNG"), "photo.png"),
        ],
    }
    res = client.post("/screen", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "Meera Iyer" in body and "Kabir Singh" in body
    assert body.index("Meera Iyer") < body.index("Kabir Singh")
    assert "photo.png" in body  # reported as skipped

    csv_res = client.get("/results/1/csv")
    assert csv_res.status_code == 200
    assert csv_res.mimetype == "text/csv"
    assert "Meera Iyer" in csv_res.get_data(as_text=True).splitlines()[1]


def test_validation(client):
    res = client.post("/screen", data={"job_description": ""}, follow_redirects=True)
    assert b"Please paste the job description" in res.data


def test_demo_and_history(client):
    res = client.post("/demo", follow_redirects=True)
    assert res.status_code == 200 and b"Aarav Sharma" in res.data
    hist = client.get("/history")
    assert b"Python Developer (Sample)" in hist.data
    client.post("/history/1/delete")
    assert client.get("/results/1").status_code == 404
