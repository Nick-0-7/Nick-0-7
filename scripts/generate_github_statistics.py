import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from xml.sax.saxutils import escape


USERNAME = "Nick-0-7"
OUTPUT = "assets/github-statistics.svg"

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Nick-0-7-github-statistics"
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def github_api(url):
    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def github_post(url, payload):
    data = json.dumps(payload).encode("utf-8")

    headers = dict(HEADERS)
    headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def github_search_count(query):
    encoded_query = urllib.parse.quote(query)

    url = (
        "https://api.github.com/search/issues"
        f"?q={encoded_query}"
        "&per_page=1"
    )

    data = github_api(url)

    return data.get("total_count", 0)


def github_commit_search_count(query):
    encoded_query = urllib.parse.quote(query)

    url = (
        "https://api.github.com/search/commits"
        f"?q={encoded_query}"
        "&per_page=1"
    )

    data = github_api(url)

    return data.get("total_count", 0)


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

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{name}/languages"
    )

    try:
        return github_api(url)
    except Exception:
        return {}


def get_contribution_count():

    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """

    payload = {
        "query": query,
        "variables": {
            "login": USERNAME
        }
    }

    try:

        data = github_post(
            "https://api.github.com/graphql",
            payload
        )

        user = data.get("data", {}).get("user")

        if user:

            calendar = (
                user
                .get("contributionsCollection", {})
                .get("contributionCalendar", {})
            )

            return calendar.get(
                "totalContributions",
                0
            )

    except Exception as error:

        print(
            "Warning: Could not retrieve "
            f"contribution calendar: {error}"
        )

    return 0


def get_statistics(user, repositories):

    one_year_ago = (
        datetime.utcnow() -
        timedelta(days=365)
    ).strftime("%Y-%m-%d")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    date_range = (
        f"{one_year_ago}..{today}"
    )

    print("Counting commits...")

    commits = github_commit_search_count(
        f"author:{USERNAME} "
        f"committer-date:{date_range}"
    )

    print("Counting pull requests...")

    pull_requests = github_search_count(
        f"author:{USERNAME} "
        f"type:pr "
        f"created:{date_range}"
    )

    print("Counting issues...")

    issues = github_search_count(
        f"author:{USERNAME} "
        f"type:issue "
        f"created:{date_range}"
    )

    print("Getting GitHub contribution count...")

    contributions = get_contribution_count()

    # If GraphQL is unavailable, use commits as a
    # safe fallback rather than displaying an incorrect
    # contribution value of zero.
    if contributions == 0 and commits > 0:
        contributions = commits

    return {
        "repositories": user.get(
            "public_repos",
            0
        ),

        "stars": sum(
            repo.get(
                "stargazers_count",
                0
            )
            for repo in repositories
        ),

        "forks": sum(
            repo.get(
                "forks_count",
                0
            )
            for repo in repositories
        ),

        "followers": user.get(
            "followers",
            0
        ),

        "commits": commits,

        "pull_requests": pull_requests,

        "issues": issues,

        "contributions": contributions
    }


def get_language_percentages(repositories):

    totals = {}

    for repo in repositories:

        if repo.get("fork"):
            continue

        if repo.get("archived"):
            continue

        print(
            f"Processing languages: "
            f"{repo['name']}"
        )

        languages = get_languages(repo)

        for language, amount in languages.items():

            totals[language] = (
                totals.get(language, 0)
                + amount
            )

    total = sum(totals.values())

    if total == 0:
        return []

    sorted_languages = sorted(
        totals.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return [
        (
            language,
            amount / total * 100
        )
        for language, amount
        in sorted_languages[:6]
    ]


def format_number(number):
    return f"{number:,}"


def create_svg(stats, languages):

    width = 1100
    height = 470

    svg = []

    svg.append(
        f'''
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}"
     height="{height}"
     viewBox="0 0 {width} {height}">
'''
    )

    # Background
    svg.append("""
<rect width="1100"
      height="470"
      rx="16"
      fill="#070d18"/>

<text x="30"
      y="48"
      fill="#f8fafc"
      font-family="Arial, Helvetica, sans-serif"
      font-size="26"
      font-weight="700">
  GITHUB STATISTICS
</text>

<text x="30"
      y="73"
      fill="#94a3b8"
      font-family="Arial, Helvetica, sans-serif"
      font-size="13">
  Live GitHub activity generated automatically.
</text>

<line x1="30"
      y1="94"
      x2="1070"
      y2="94"
      stroke="#263449"/>

<line x1="30"
      y1="95"
      x2="1070"
      y2="95"
      stroke="#00c2ff"
      stroke-width="2"/>
""")

    # Statistics cards
    cards = [
        (
            "COMMITS",
            stats["commits"],
            "#3178C6"
        ),
        (
            "CONTRIBUTIONS",
            stats["contributions"],
            "#00C2FF"
        ),
        (
            "PULL REQUESTS",
            stats["pull_requests"],
            "#A78BFA"
        ),
        (
            "ISSUES",
            stats["issues"],
            "#F97316"
        ),
        (
            "REPOSITORIES",
            stats["repositories"],
            "#22C55E"
        ),
        (
            "STARS",
            stats["stars"],
            "#F7DF1E"
        )
    ]

    positions = [
        (30, 120),
        (380, 120),
        (730, 120),
        (30, 215),
        (380, 215),
        (730, 215)
    ]

    for (
        label,
        value,
        accent
    ), (
        x,
        y
    ) in zip(cards, positions):

        svg.append(
            f'''
<rect x="{x}"
      y="{y}"
      width="320"
      height="75"
      rx="12"
      fill="#0b1626"
      stroke="#20344d"/>

<rect x="{x}"
      y="{y}"
      width="4"
      height="75"
      rx="2"
      fill="{accent}"/>

<text x="{x + 18}"
      y="{y + 23}"
      fill="#8ea6bf"
      font-family="Arial, Helvetica, sans-serif"
      font-size="9">
  {label}
</text>

<text x="{x + 18}"
      y="{y + 55}"
      fill="{accent}"
      font-family="Arial, Helvetica, sans-serif"
      font-size="24"
      font-weight="700">
  {format_number(value)}
</text>
'''
        )

    # Language section
    svg.append("""
<rect x="30"
      y="315"
      width="1040"
      height="110"
      rx="12"
      fill="#091221"
      stroke="#1f3148"/>

<text x="50"
      y="342"
      fill="#f8fafc"
      font-family="Arial, Helvetica, sans-serif"
      font-size="15"
      font-weight="700">
  Most Used Languages
</text>
""")

    colors = [
        "#3178C6",
        "#F7DF1E",
        "#E34F26",
        "#3776AB",
        "#1572B6",
        "#A78BFA"
    ]

    bar_x = 50
    bar_y = 360
    bar_width = 850

    if languages:

        current_x = bar_x

        for index, (
            language,
            percentage
        ) in enumerate(languages):

            segment_width = (
                bar_width *
                percentage /
                100
            )

            svg.append(
                f'''
<rect x="{current_x}"
      y="{bar_y}"
      width="{segment_width}"
      height="12"
      fill="{colors[index % len(colors)]}"/>
'''
            )

            current_x += segment_width

        label_x = 50

        for index, (
            language,
            percentage
        ) in enumerate(languages):

            svg.append(
                f'''
<circle cx="{label_x}"
        cy="400"
        r="5"
        fill="{colors[index % len(colors)]}"/>

<text x="{label_x + 12}"
      y="404"
      fill="#dce7f2"
      font-family="Arial, Helvetica, sans-serif"
      font-size="10">
  {escape(language)} {percentage:.1f}%
</text>
'''
            )

            label_x += 145

    svg.append("""
<text x="930"
      y="405"
      fill="#52677e"
      font-family="Arial, Helvetica, sans-serif"
      font-size="9">
  Updated automatically
</text>

</svg>
""")

    return "\n".join(svg)


def main():

    os.makedirs(
        "assets",
        exist_ok=True
    )

    print()
    print("======================================")
    print("Generating GitHub Statistics")
    print("======================================")

    print("Fetching GitHub profile...")

    user = get_user()

    print("Fetching repositories...")

    repositories = get_repositories()

    print(
        f"Found {len(repositories)} repositories."
    )

    print("Calculating statistics...")

    stats = get_statistics(
        user,
        repositories
    )

    print()
    print("Statistics:")
    print(
        f"  Commits: {stats['commits']}"
    )
    print(
        f"  Contributions: "
        f"{stats['contributions']}"
    )
    print(
        f"  Pull Requests: "
        f"{stats['pull_requests']}"
    )
    print(
        f"  Issues: {stats['issues']}"
    )
    print(
        f"  Repositories: "
        f"{stats['repositories']}"
    )
    print(
        f"  Stars: {stats['stars']}"
    )

    print()
    print("Calculating language profile...")

    languages = get_language_percentages(
        repositories
    )

    print("Generating SVG...")

    svg = create_svg(
        stats,
        languages
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg)

    print()
    print("======================================")
    print("GitHub Statistics generated!")
    print(f"Output: {OUTPUT}")
    print("======================================")


if __name__ == "__main__":
    main()
