from concurrent.futures import ThreadPoolExecutor

from src.common.id_generator import generator


def main():
    with ThreadPoolExecutor(max_workers=20) as executor:
        ids = list(executor.map(lambda _: generator.next_id(), range(100_000)))
    assert len(ids) == len(set(ids)), "duplicate snowflake ids detected"
    print(f"generated {len(ids)} unique ids")


if __name__ == "__main__":
    main()
