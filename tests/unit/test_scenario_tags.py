from tag_check import untagged_scenarios


def test_every_scenario_has_an_issue_tag():
    assert untagged_scenarios() == []
