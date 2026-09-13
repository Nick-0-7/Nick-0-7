import json
import math
import os
import urllib.request
from xml.sax.saxutils import escape


USERNAME = "Nick-0-7"
OUTPUT = "assets/engineering-metrics.svg"

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Nick-0-7-engineering-metrics"
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def github_api(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def get_user():
    return github_api(
        f"https://api.github.com/users/{USERNAME}"
    )


def get_repositories():
    repositories = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?per_page=100&page={page}&sort=updated"
        )

        data = github_api(url)

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


def get_languages(repo):
    owner = repo["owner"]["login"]
    name = repo["name"]

    url = f"https://api.github.com/repos/{owner}/{name}/languages"

    try:
        return github_api(url)
    except Exception:
        return {}


def format_number(number):
    return f"{number:,}"


def language_color(index):
    colors = [
        "#3178C6",
        "#F7DF1E",
        "#E34F26",
        "#3776AB",
        "#1572B6",
        "#ED8B00",
        "#00ADD8",
        "#A8B9CC",
        "#563D7C",
        "#DA5B0B"
    ]

    return colors[index % len(colors)]


def create_svg(user, repositories, language_totals):

    public_repositories = user.get("public_repos", 0)
    followers = user.get("followers", 0)

    active_repositories = [
        repo for repo in repositories
        if not repo.get("archived", False)
        and not repo.get("fork", False)
    ]

    total_stars = sum(
        repo.get("stargazers_count", 0)
        for repo in repositories
    )

    total_forks = sum(
        repo.get("forks_count", 0)
        for repo in repositories
    )

    active_count = len(active_repositories)

    total_language_bytes = sum(language_totals.values())

    language_data = []

    if total_language_bytes > 0:

        sorted_languages = sorted(
            language_totals.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for language, amount in sorted_languages[:7]:

            percentage = (
                amount / total_language_bytes
            ) * 100

            language_data.append(
                (language, percentage)
            )

    width = 1100
    height = 700

    svg = []

    svg.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}">'''
    )

    svg.append("""
    <rect width="1100" height="700" rx="16"
          fill="#070d18"/>

    <text x="30" y="55"
          fill="#f8fafc"
          font-family="Arial, Helvetica, sans-serif"
          font-size="29"
          font-weight="700">
        05 · ENGINEERING METRICS
    </text>

    <text x="30" y="82"
          fill="#94a3b8"
          font-family="Arial, Helvetica, sans-serif"
          font-size="14">
        Live repository signals generated from GitHub activity.
    </text>

    <line x1="30" y1="103"
          x2="1070" y2="103"
          stroke="#263449"
          stroke-width="1"/>

    <line x1="30" y1="104"
          x2="1070" y2="104"
          stroke="#00c2ff"
          stroke-width="2"/>
    """)

    # Main metrics panel
    svg.append("""
    <rect x="30" y="125"
          width="1040"
          height="150"
          rx="16"
          fill="#091221"
          stroke="#1f3148"/>

    <text x="50" y="155"
          fill="#f8fafc"
          font-family="Arial, Helvetica, sans-serif"
          font-size="17"
          font-weight="700">
        GitHub Engineering Metrics
    </text>
    """)

    metrics = [
        ("PUBLIC REPOSITORIES", public_repositories),
        ("TOTAL STARS", total_stars),
        ("TOTAL FORKS", total_forks),
        ("FOLLOWERS", followers),
        ("ACTIVE REPOSITORIES", active_count),
    ]

    metric_x = [50, 250, 450, 650, 850]

    for index, ((label, value), x) in enumerate(
        zip(metrics, metric_x)
    ):

        svg.append(
            f'''
            <rect x="{x}" y="170"
                  width="180"
                  height="85"
                  rx="12"
                  fill="#0b1626"
                  stroke="#20344d"/>

            <rect x="{x}" y="170"
                  width="4"
                  height="85"
                  rx="2"
                  fill="{language_color(index)}"/>

            <text x="{x + 16}" y="192"
                  fill="#8eb7d9"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="9">
                {escape(label)}
            </text>

            <text x="{x + 16}" y="225"
                  fill="{language_color(index)}"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="24"
                  font-weight="700">
                {format_number(value)}
            </text>

            <text x="{x + 16}" y="243"
                  fill="#60748c"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="8">
                GitHub profile signal
            </text>
            '''
        )

    # Language panel
    svg.append("""
    <rect x="30" y="295"
          width="1040"
          height="350"
          rx="16"
          fill="#091221"
          stroke="#1f3148"/>

    <text x="50" y="330"
          fill="#f8fafc"
          font-family="Arial, Helvetica, sans-serif"
          font-size="17"
          font-weight="700">
        Language Profile
    </text>

    <text x="50" y="350"
          fill="#71849a"
          font-family="Arial, Helvetica, sans-serif"
          font-size="10">
        Aggregated by bytes across active, non-fork repositories.
    </text>
    """)

    # Language bars
    bar_x = 160
    bar_width = 350
    start_y = 385
    row_height = 37

    for index, (language, percentage) in enumerate(language_data):

        y = start_y + index * row_height
        label = escape(language)

        svg.append(
            f'''
            <text x="50" y="{y + 7}"
                  fill="#dce7f2"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="11"
                  font-weight="600">
                {label}
            </text>

            <rect x="{bar_x}" y="{y - 3}"
                  width="{bar_width}"
                  height="9"
                  rx="5"
                  fill="#16283e"/>

            <rect x="{bar_x}" y="{y - 3}"
                  width="{max(2, bar_width * percentage / 100)}"
                  height="9"
                  rx="5"
                  fill="{language_color(index)}"/>

            <text x="530" y="{y + 7}"
                  fill="#dce7f2"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="10"
                  font-weight="600">
                {percentage:.1f}%
            </text>
            '''
        )

    # Donut chart
    cx = 775
    cy = 495
    radius = 78
    circumference = 2 * math.pi * radius

    svg.append(
        f'''
        <circle cx="{cx}" cy="{cy}"
                r="{radius}"
                fill="none"
                stroke="#14253a"
                stroke-width="28"/>
        '''
    )

    offset = 0

    for index, (language, percentage) in enumerate(language_data):

        segment = circumference * percentage / 100

        svg.append(
            f'''
            <circle cx="{cx}" cy="{cy}"
                    r="{radius}"
                    fill="none"
                    stroke="{language_color(index)}"
                    stroke-width="28"
                    stroke-dasharray="{segment} {circumference - segment}"
                    stroke-dashoffset="{-offset}"
                    transform="rotate(-90 {cx} {cy})"/>
            '''
        )

        offset += segment

    svg.append("""
    <circle cx="775" cy="495"
            r="48"
            fill="#091221"/>

    <text x="775" y="489"
          text-anchor="middle"
          fill="#f8fafc"
          font-family="Arial, Helvetica, sans-serif"
          font-size="17"
          font-weight="700">
        100%
    </text>

    <text x="775" y="508"
          text-anchor="middle"
          fill="#8da1b7"
          font-family="Arial, Helvetica, sans-serif"
          font-size="9">
        LANGUAGE MIX
    </text>
    """)

    # Language legend
    legend_x = 870
    legend_y = 390

    for index, (language, percentage) in enumerate(language_data):

        y = legend_y + index * 27

        svg.append(
            f'''
            <circle cx="{legend_x}"
                    cy="{y - 4}"
                    r="5"
                    fill="{language_color(index)}"/>

            <text x="{legend_x + 14}" y="{y}"
                  fill="#dce7f2"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="10">
                {escape(language)}
            </text>

            <text x="1015" y="{y}"
                  text-anchor="end"
                  fill="#dce7f2"
                  font-family="Arial, Helvetica, sans-serif"
                  font-size="10"
                  font-weight="600">
                {percentage:.1f}%
            </text>
            '''
        )

    svg.append("""
    <text x="50" y="625"
          fill="#52677e"
          font-family="Arial, Helvetica, sans-serif"
          font-size="9">
        Automatically generated with GitHub Actions · No manual edits required.
    </text>

    </svg>
    """)

    return "\n".join(svg)


def main():

    os.makedirs("assets", exist_ok=True)

    print("Fetching GitHub profile...")
    user = get_user()

    print("Fetching repositories...")
    repositories = get_repositories()

    # Exclude forks from language aggregation
    active_repositories = [
        repo for repo in repositories
        if not repo.get("archived", False)
        and not repo.get("fork", False)
    ]

    language_totals = {}

    print(
        f"Processing languages for "
        f"{len(active_repositories)} repositories..."
    )

    for repo in active_repositories:

        print(f"  → {repo['name']}")

        languages = get_languages(repo)

        for language, amount in languages.items():

            language_totals[language] = (
                language_totals.get(language, 0)
                + amount
            )

    svg = create_svg(
        user,
        repositories,
        language_totals
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(svg)

    print()
    print("===================================")
    print("Engineering Metrics generated!")
    print(f"Output: {OUTPUT}")
    print("===================================")


if __name__ == "__main__":
    main()
