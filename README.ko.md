<div align="center">

<img src="https://raw.githubusercontent.com/elfenomenokim/process-birth/main/docs/logo.svg" width="96" height="96" alt="process-birth: 같은 프로세스의 두 관측이 하나의 시각으로 모인다">

# process-birth

프로세스 시작 시각을 UTC 초 하나로 바꿔, 재사용된 PID를 같은 프로세스로 착각하지 않게 하는 파이썬 모듈.

[English](README.md) · Python 3.9+

[![pypi](https://img.shields.io/pypi/v/process-birth?label=pypi)](https://pypi.org/project/process-birth/)
[![tests](https://github.com/elfenomenokim/process-birth/actions/workflows/tests.yml/badge.svg)](https://github.com/elfenomenokim/process-birth/actions/workflows/tests.yml)
[![license](https://img.shields.io/github/license/elfenomenokim/process-birth)](LICENSE)

[설치](#설치) · [빠른-시작](#빠른-시작) · [왜-필요한가](#왜-필요한가) · [레퍼런스](#레퍼런스)

</div>

`ps` 한 줄을 해석하는 비용은 최소 3.5µs, 중앙값 3.9µs입니다. 프로세스 1077개의 스냅샷 한 번은 51ms였습니다. 두 값은 `docs/bench/identity.json`에 저장되어 있습니다.

PID는 신원이 아닙니다. 운영체제가 그 번호를 다시 쓰기 때문에, 저장해 둔 `1234`가 오늘은 편집기였다가 내일은 빌드 작업자가 될 수 있습니다. 이 모듈은 프로세스를 정수 하나로 줄입니다. 그 프로세스가 시작한 UTC 기준 초입니다. 같은 프로세스를 두 번 관측하면 두 값이 같고, PID는 같지만 시작 시각이 다르면 다릅니다.

파일 하나, 표준 라이브러리만 씁니다. 그래서 원격 번들에 그대로 넣어 바로 실행할 수 있습니다.

## 설치

```sh
pip install process-birth
```

Python 3.9 이상, 의존성 없음. macOS arm64 · Python 3.12에서 확인했습니다.

## 빠른 시작

```python
import process_birth

start = process_birth.epoch("Sat Sep 26 11:54:39 2026", legacy_zone="UTC")
print(start)                                   # 1790423679

print(process_birth.read(1) is not None)       # True: 이 호스트에 pid 1이 있다
print(process_birth.same(start, start))        # True
print(process_birth.same(None, None))          # False: 값이 없는 둘은 절대 같지 않다
```

저장해 둔 값과 살아 있는 프로세스를 비교하는 것이 이 모듈의 목적입니다.

```python
import process_birth

saved = 1790423679                  # 창을 열 때 기록한 값
if process_birth.same(saved, process_birth.read(1234)):
    print("같은 프로세스가 아직 pid 1234를 쥐고 있다")
else:
    print("pid 1234는 사라졌거나 다른 프로세스가 가져갔다")
```

비교가 여러 번이면 스냅샷을 한 번만 뜹니다.

```python
import process_birth

rows = process_birth.snapshot()      # {pid: (birth_epoch, parent_pid)}
for pid, (birth, parent) in rows.items():
    if birth > 1790423679:
        print(f"pid {pid} (부모 {parent})가 저장된 프로세스 뒤에 시작했다")
```

## 왜 필요한가

PID로 프로세스를 감시하는 코드에는 운영체제와의 경쟁이 있습니다. 창의 PID를 읽은 뒤 신호를 보내기 전에 프로세스가 끝나고 그 번호가 다시 쓰일 수 있습니다. 그러면 신호는 관계없는 프로세스에 도착합니다.

세 가지 성질이 흔한 어중간한 해법을 피합니다.

- **문자열이 아니라 정수 하나.** `ps` 출력은 로케일, `LC_ALL`, GNU와 BSD에 따라 다릅니다. 파싱해서 UTC 초 하나로 만들면 비교가 숫자 비교가 되고, 시간대 질문 자체가 사라집니다.
- **없는 값은 절대 같지 않습니다.** `same(None, None)`은 `False`입니다. 실패한 관측 둘은 모르는 값 둘이지, 같은 프로세스라는 증거가 아닙니다. "둘 다 비었으니 일치"로 처리하는 코드가 사라진 창과 새로 생긴 창을 헷갈리게 만듭니다.
- **요일을 실제로 검사합니다.** `ps` 한 줄에는 요일 이름이 들어 있습니다. 파서는 그 요일을 실제 날짜와 대조해서 어긋나면 그 줄을 거부합니다. 잘리거나 밀린 출력을 받아들이는 대신 잡아냅니다.

저장된 주소 텍스트(`target_text`)는 일부러 분리해 두었습니다. 터미널 끝점을 가리키는 불투명한 해시 재료이지 신원 값이 아니며, 예전 버전이 기록한 값과 모양이 같게 유지됩니다.

## 레퍼런스

### `epoch(value, *, legacy_zone="local", weekdays=None, parse=None)`

시작 시각의 유닉스 초를 돌려주고, 모르는 값이거나 잘못되었거나 실제 날짜가 아니면 `None`을 돌려줍니다.

| 입력 | 결과 |
| --- | --- |
| 양의 `int` | 그대로 |
| 숫자 문자열 | 정수, 0 이하는 `None` |
| `Sat Sep 26 11:54:39 2026` | 그 시각의 유닉스 초 |
| `2026년 9월 26일 토요일 11시 54분 39초` | 같은 시각, 한국어 `ps` 모양 |
| 요일이 어긋난 줄 | `None` |
| 그 밖 | `None` |

`legacy_zone`은 `"UTC"` 또는 `"local"`입니다. `ps`에서 읽은 값은 UTC이고, `"local"`은 UTC로 바꾸기 전에 기록된 저장값을 지역 시계로 왕복시키기 위해 남아 있습니다.

### `read(pid, *, weekdays=None, parse=None)`

`LC_ALL=C`, `TZ=UTC`로 `ps -p <pid> -o lstart=`를 실행해 시작 초를 돌려줍니다. 쓸 수 없는 pid이거나 호출이 실패하면 `None`.

### `same(first, second, *, first_zone="local", second_zone="local", weekdays=None, parse=None)`

두 값이 모두 해석되고 초가 같을 때만 참입니다.

### `snapshot(*, weekdays=None, parse=None)`

`ps -axo pid=,ppid=,lstart=` 한 번으로 `{pid: (birth_epoch, parent_pid)}`를 만듭니다. 해석하지 못한 줄은 건너뜁니다.

### `target_text(value, *, weekdays=None, render=None)`

저장된 주소 텍스트를 C/로컬 `ps` 모양(`Sat Sep 26 20:54:39 2026`)으로 렌더링합니다. 숫자 문자열이 아닌 값은 그대로 돌려줍니다. 저장된 텍스트는 불투명한 주소 재료이기 때문입니다. 다른 모양이 필요하면 `render(epoch_seconds)`를 주십시오.

### 다른 `ps` 로케일

```python
FRENCH = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]

def parse_french(text):
    # (년, 월, 일, 요일이름, 시, 분, 초) 또는 None 을 돌려준다
    ...

process_birth.epoch("sam 26 sept. 2026 11:54:39",
                    legacy_zone="UTC", weekdays=FRENCH, parse=parse_french)
```

`weekdays`는 월요일부터 시작하는 이름 일곱 개입니다. `parse`는 내장 형식이 하나도 맞지 않을 때만 불립니다. `(년, 월, 일, 요일_또는_None, 시, 분, 초)`를 돌려주십시오.

### 명령행

```sh
python3 process_birth.py snapshot
python3 process_birth.py read PID
python3 process_birth.py epoch "Sat Sep 26 11:54:39 2026" UTC
python3 process_birth.py same A B
python3 process_birth.py target-text 1790423679
```

값을 모르거나 두 값이 다르면 종료 상태 1입니다.

## 숫자

2026-11-19, macOS arm64(M5 Pro), Python 3.12.8에서 쟀습니다. 값은 `docs/bench/identity.json`에 있습니다.

| 항목 | 결과 |
| --- | --- |
| C 형식 `ps` 줄에 `epoch()` | 최소 3.46µs, 중앙값 3.92µs (2000회) |
| 살아 있는 호스트에 `snapshot()` | 1077행, 51ms |
| `epoch("not a date")`, `read(-1)` | `None`, `None` |
| `same(None, None)` | `False` |

## 한계

- **시각을 읽는 곳.** macOS, Linux, BSD는 C 로케일·UTC로 `ps -o lstart`를 읽습니다. `ps`가 없는 Linux(최소 컨테이너)는 `/proc/<pid>/stat`의 22번 필드를 procps와 같은 계산으로 읽어서, 두 경로가 같은 초를 냅니다. Windows의 `read()`는 GetProcessTimes의 생성 시각을 씁니다. Windows에서 `snapshot()`은 `OSError`를 냅니다.
- **1초 해상도.** 같은 초에 시작한 두 프로세스는 구별하지 못합니다. `ps`가 알려 주는 해상도가 그렇습니다.
- **권한 검사가 없습니다.** 프로세스를 볼 수 있는 사람은 시작 시각도 볼 수 있습니다. 인증 수단이 아닙니다.
- **요일 대조는 실제 달력 날짜를 전제합니다.** 요일을 지어낸 `ps` 출력은 의도적으로 거부됩니다.
- **검증.** 테스트는 macOS, Ubuntu, Windows에서 통과합니다. Ubuntu 24.04에서는 살아 있는 프로세스 222개 모두 `/proc` 경로와 `ps`가 같은 값을 냈습니다. 시간 측정은 macOS의 `ps`만 했습니다.
- **서머타임 겹침.** 가을에 반복되는 현지 시각을 `epoch(text, legacy_zone="local")`로 바꾸면 두 시각 중 하나를 고릅니다. 실제 프로세스 읽기에는 영향이 없습니다. `read()`와 `snapshot()`은 항상 `ps`에 UTC로 묻습니다.

## 자주 묻는 질문

**왜 타임스탬프 문자열이 아니라 UTC 초입니까?** 문자열 비교는 로케일, 공백, 시간대에 좌우됩니다. 정수 하나로 파싱하면 시간대 질문이 사라지고, 같은 방식으로 렌더링되었다는 이유만으로 오래된 값이 같아 보이는 일도 없습니다.

**`same(None, None)`이 왜 거짓입니까?** 실패한 관측 둘은 모르는 값 둘입니다. 둘을 일치로 처리하는 것이 같은 자리의 죽은 창과 새 창을 헷갈리게 만듭니다.

**`target_text`는 신원입니까?** 아닙니다. 저장된 값의 모양을 유지해야 하는 불투명한 주소 재료입니다. 신원에는 `epoch()`와 `same()`을 쓰십시오.

## 기여

버그 보고와 패치를 환영합니다. 동작 변경에 필요한 픽스처는 [CONTRIBUTING.md](CONTRIBUTING.md)에 있습니다.

## 라이선스

MIT, [LICENSE](LICENSE).
