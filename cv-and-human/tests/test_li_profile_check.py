from li_profile_check import count_chars, utf16_slice


def test_count_chars_matches_js_string_length():
    # JS String.prototype.length counts UTF-16 code units.
    assert count_chars("abc") == 3            # plain ASCII
    assert count_chars("café") == 4           # U+00E9, one code unit
    assert count_chars("🚀") == 2             # surrogate pair, TWO in JS
    assert count_chars("\r\n") == 2           # CRLF is two characters
    assert count_chars("") == 0


def test_count_chars_differs_from_python_len_on_emoji():
    # The whole reason this function exists.
    text = "Platform Engineer 🚀"
    assert len(text) == 19
    assert count_chars(text) == 20


def test_utf16_slice_does_not_split_a_surrogate_pair():
    text = "ab🚀cd"
    # 3 code units = "ab" plus half of the rocket; the half is dropped, not mangled.
    assert utf16_slice(text, 3) == "ab"
    assert utf16_slice(text, 4) == "ab🚀"
    assert utf16_slice(text, 99) == text


def test_check_field_flags_over_limit():
    from li_profile_check import LIMITS, check_field
    result = check_field("headline", "x" * 225)
    assert result["ok"] is False
    assert result["count"] == 225
    assert result["limit"] == LIMITS["headline"]
    assert result["over_by"] == 5


def test_check_field_passes_under_limit():
    from li_profile_check import check_field
    result = check_field("headline", "Platform Engineer who cut AWS spend 38%")
    assert result["ok"] is True
    assert result["over_by"] == 0


def test_front_load_passes_when_claim_is_above_the_fold():
    from li_profile_check import FOLD, check_front_load
    about = "I cut a fintech's AWS bill by 38%. " + ("filler. " * 60)
    result = check_front_load(about, ["38%"])
    assert result["ok"] is True
    assert result["missing"] == []
    assert count_chars(result["visible"]) <= FOLD


def test_front_load_fails_when_claim_is_buried_below_the_fold():
    from li_profile_check import check_front_load
    about = ("Experienced professional. " * 20) + "I cut AWS spend 38%."
    result = check_front_load(about, ["38%"])
    assert result["ok"] is False
    assert result["missing"] == ["38%"]


def test_keyword_coverage_reports_which_field_carries_each_keyword():
    from li_profile_check import keyword_coverage
    fields = {
        "headline": "Platform Engineer",
        "about": "I run Terraform across three clouds.",
        "skills": "Kubernetes",
    }
    rows = {r["keyword"]: r for r in keyword_coverage(["Terraform", "Kubernetes", "Go"], fields)}
    assert rows["Terraform"]["fields"] == ["about"]
    assert rows["Kubernetes"]["fields"] == ["skills"]
    assert rows["Go"]["fields"] == []
    assert rows["Go"]["covered"] is False


def test_keyword_coverage_is_case_insensitive():
    from li_profile_check import keyword_coverage
    rows = keyword_coverage(["terraform"], {"about": "We use Terraform daily."})
    assert rows[0]["covered"] is True


def test_check_skills_flags_only_the_overlong_skill():
    from li_profile_check import check_skills
    results = check_skills(["Kubernetes", "x" * 85])
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
    assert results[1]["over_by"] == 5


def test_check_profile_is_not_ok_when_any_check_fails():
    from li_profile_check import check_profile
    results = check_profile({
        "headline": "x" * 300,
        "about": "short",
        "skills": ["Kubernetes"],
        "keywords": ["Terraform"],
        "must_contain": [],
    })
    assert results["ok"] is False
    assert results["coverage"][0]["covered"] is False


def test_check_profile_is_ok_on_a_clean_draft():
    from li_profile_check import check_profile
    results = check_profile({
        "headline": "Platform Engineer who cut a fintech's AWS spend 38%",
        "about": "I cut a fintech's AWS spend 38% and own their Terraform monorepo.",
        "skills": ["Terraform", "Kubernetes"],
        "keywords": ["Terraform"],
        "must_contain": ["38%"],
    })
    assert results["ok"] is True
