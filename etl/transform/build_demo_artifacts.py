from __future__ import annotations

from service.housing_data import write_demo_artifacts


def main() -> None:
    bundle = write_demo_artifacts()
    overview = bundle.overview
    print(
        "Generated demo artifacts for "
        f"{overview['summary']['counties_covered']} counties in {overview['latest_period']}"
    )


if __name__ == "__main__":
    main()
