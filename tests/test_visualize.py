"""visualize 模块测试。"""

import pandas as pd

from yei.visualize import plot_yeoi_ranking


def test_plot_yeoi_ranking_writes_file(tmp_path):
    scores = pd.DataFrame(
        {
            "city": ["A", "B"],
            "year": [2025, 2025],
            "yeoi_score": [80.0, 60.0],
        }
    )
    path = plot_yeoi_ranking(scores, 2025, tmp_path)
    assert path.exists()
    assert path.name == "yeoi_ranking_2025.png"
