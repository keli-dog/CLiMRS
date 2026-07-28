# CLiMRS 运行排错记录

> 覆盖环境：  
> - WSL2（`ubuntu22@CHINAMI-GIRKPMJ`，路径 `/mnt/e/gengzeyu/CLiMRS/...`）  
> - 原生 Linux（`ubuntu@ubuntu`，路径 `/media/ubuntu/Student/gengzeyu/CLiMRS`）  
> Conda：`climrs`（Python 3.8 + torch 1.8.1+cu111）  
> 更新日期：2026-07-28

---

## 一句话结论

**原生 Linux + RTX 4090 上已跑通 `--test` 回放**；LLM 导入与 MiniMax API 已通，规划前需 `mkdir -p log`。  
WSL 上 PhysX GPU pinned memory 问题见第 7 节，与原生 Linux 卡点不同。

---

## 标准启动环境变量

### A. 原生 Linux（4090 机，推荐）

```bash
conda activate climrs
cd /media/ubuntu/Student/gengzeyu/CLiMRS

export TORCH_CUDA_ARCH_LIST=8.6
export CLIMRS_ROOT=/media/ubuntu/Student/gengzeyu/CLiMRS
export LD_LIBRARY_PATH=$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
export PYTHONPATH=$CLIMRS_ROOT:$CLIMRS_ROOT/LLM:$CLIMRS_ROOT/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH

mkdir -p log
python climrs/run.py
```

### B. WSL2（旧路径）

```bash
conda activate climrs

export CLIMRS_HOME=/mnt/e/gengzeyu/CLiMRS
export CLIMRS_ROOT=/mnt/e/gengzeyu/CLiMRS/CLiMRS
export POSELIB_PARENT=$CLIMRS_HOME/IsaacGymEnvs/isaacgymenvs/tasks/amp
export ISAACGYM_LIB=/home/ubuntu22/CLiMRS/CLiMRS/isaacgym/python/isaacgym/_bindings/linux-x86_64

export PYTHONPATH=$POSELIB_PARENT:$CLIMRS_ROOT/LLM:$PYTHONPATH
export LD_LIBRARY_PATH=$ISAACGYM_LIB:/usr/lib/wsl/lib:$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

cd $CLIMRS_ROOT
```

---

## 问题清单与解决办法

### 1. `ModuleNotFoundError: No module named 'poselib'` / `poselib.poselib`

**原因**

- `PYTHONPATH` 未指向含外层 `poselib` 的上一级：`IsaacGymEnvs/isaacgymenvs/tasks/amp`
- 不要指到 `.../amp/poselib` 本身

**找路径**

```bash
find /media/ubuntu/Student/gengzeyu -maxdepth 6 -iname "*poselib*"
# 例：.../CLiMRS/IsaacGymEnvs/isaacgymenvs/tasks/amp/poselib
```

**解决**

```bash
export PYTHONPATH=$CLIMRS_ROOT/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH
# 若缺 __init__.py：
touch $CLIMRS_ROOT/IsaacGymEnvs/isaacgymenvs/tasks/amp/poselib/__init__.py
```

**验证**

```bash
python -c "from poselib.poselib.skeleton.skeleton3d import SkeletonMotion, SkeletonState; print('poselib ok')"
```

---

### 2. `ImportError: libpython3.8.so.1.0: cannot open shared object file`

**原因**

- conda 的 `lib` 未进 `LD_LIBRARY_PATH`（README 已写）

**解决**

```bash
export LD_LIBRARY_PATH=$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

**验证**

```bash
python -c "from isaacgym import gymapi; import torch; print('ok', torch.__version__, torch.cuda.is_available())"
```

> **必须先 import isaacgym，再 import torch**，否则报：`PyTorch was imported before isaacgym modules`。

---

### 3. `AttributeError: 'Runner' object has no attribute 'model_builder'`

**原因**

- `rl-games` 过新；项目要求 `rl-games==1.1.4`

**解决**

```bash
pip install "rl-games==1.1.4"
```

---

### 4. `ModuleNotFoundError: No module named 'env.tasks.humanoid_amp_carryobject'`

**原因**

- `parse_task.py` 顶部无条件导入了仓库中不存在的  
  `humanoid_amp_carryobject` / `share_humanoid_amp_carryobject`  
- 默认任务实际是 `HumanoidAMPCarryObjectObstacle`，不依赖上述文件

**解决**（服务器改 `climrs/utils/parse_task.py`）

```bash
cd $CLIMRS_ROOT
python - << 'EOF'
from pathlib import Path
p = Path("climrs/utils/parse_task.py")
text = p.read_text()
old = """from env.tasks.humanoid_amp_carryobject import HumanoidAMPCarryObject
from env.tasks.share_humanoid_amp_carryobject import ShareHumanoidCarryObject
from env.tasks.humanoid_amp_carryobject_obstacle import HumanoidAMPCarryObjectObstacle"""
new = """try:
    from env.tasks.humanoid_amp_carryobject import HumanoidAMPCarryObject
    from env.tasks.share_humanoid_amp_carryobject import ShareHumanoidCarryObject
except ModuleNotFoundError:
    HumanoidAMPCarryObject = None
    ShareHumanoidCarryObject = None
from env.tasks.humanoid_amp_carryobject_obstacle import HumanoidAMPCarryObjectObstacle"""
if old not in text:
    raise SystemExit("未找到目标导入语句")
p.write_text(text.replace(old, new, 1))
print("parse_task.py updated")
EOF
```

---

### 5. `pybullet.error: Cannot load URDF` / `Agent/franka_description/... not found`

**原因（多层）**

1. 代码要相对路径 `Agent/franka_description/...`、`Agent/Component_asset/...`
2. 真实资源在同级 **`Agent_asset/`**
3. 若 `Agent` 已是真实目录（含 `Franka_agent.py`），执行 `ln -s ... Agent` 会把链建到 **`Agent/` 内部**，而不是替换 `Agent`
4. URDF 里 `package://franka_description/meshes/` 对 pybullet/Isaac 不友好

**正确做法（保留 Agent 目录内已有文件）**

```bash
cd $CLIMRS_ROOT

# 删掉误建的嵌套软链
rm -f Agent/Agent_asset

# 把资源目录链进 Agent
ln -sfn ../Agent_asset/franka_description Agent/franka_description
ln -sfn ../Agent_asset/Component_asset Agent/Component_asset
ln -sfn ../Agent_asset/tracer_mini Agent/tracer_mini

ls Agent/franka_description/robots/franka_panda.urdf
ls Agent/Component_asset | head

cp -n Agent/franka_description/robots/franka_panda.urdf \
      Agent/franka_description/robots/franka_panda.urdf.bak
sed -i 's|package://franka_description/meshes/|../meshes/|g' \
  Agent/franka_description/robots/franka_panda.urdf
```

**若 Agent 本身可整目录替换为软链（WSL 旧方案）**

```bash
rm -rf Agent   # 注意：会丢掉 Agent 下自有文件，先确认
ln -sfn "$PWD/Agent_asset" Agent
```

---

### 6. `rtree.exceptions.RTreeError: Coordinates must be in the form (minx, miny, ...)`

**原因**

- `paths1` 终点是 **3D** `(x,y,z)`，经 `start_positions` 传入 `plan_path_to_franka`
- RRT / rtree 搜索空间是 **2D**，`v + v` 坐标格式非法

**解决**（改 `climrs/rrt_algorithms/planpath.py` 中 `plan_path_to_franka`）

将 `robot_pos` / `push_target` **强制截成 2D tuple**：

```python
if start_pos is not None:
    robot_pos = tuple(np.asarray(start_pos).flatten()[:2])
else:
    robot_idx = gym.get_actor_index(env_ptr, robot_handle, gymapi.DOMAIN_SIM)
    robot_pos = tuple(root_state[robot_idx, 0:2].cpu().numpy())
box_idx = gym.get_actor_index(env_ptr, box_handle, gymapi.DOMAIN_SIM)
box_pos = tuple(root_state[box_idx, 0:2].cpu().numpy())

if custom_push_target is not None:
    push_target = tuple(np.asarray(custom_push_target).flatten()[:2])
else:
    push_target = box_pos
```

服务器可用对话中给出的整段 `python <<'EOF'` patch。

> 仍可能出现 `Could not connect to goal` / `RRT planning failed, using default paths`：规划失败会回退默认路径，**不阻断** play，但路径非最优。

---

### 7. `nvrtc: error: invalid value for --gpu-architecture (-arch)`

**原因**

- **RTX 4090 = sm_89**，**torch 1.8.1 + CUDA 11.1** 的 NVRTC 不认 8.9
- 仅 Python 层伪装 `get_device_capability` **不够**（C++ 仍读真实算力）
- `runpy.run_path` 包装还会导致 `No module named 'utils'`，不要用

**解决：在 `climrs/run.py` 最顶部禁用 JIT（isaacgym 先于 torch）**

```bash
cd $CLIMRS_ROOT
python - << 'EOF'
from pathlib import Path
p = Path("climrs/run.py")
text = p.read_text()
header = '''from isaacgym import gymapi
import torch
# RTX 4090 + cu111: disable JIT to avoid nvrtc sm_89 error
def _jit_noop(o=None, **kw):
    return (lambda f: f) if o is None else o
torch.jit.script = _jit_noop
torch.cuda.get_device_capability = lambda *a, **k: (8, 6)

'''
if "def _jit_noop" not in text:
    p.write_text(header + text)
    print("run.py: disabled torch.jit.script")
else:
    print("already patched")
EOF

export TORCH_CUDA_ARCH_LIST=8.6
python climrs/run.py
```

---

### 8. WSL：`Failed to allocate pinned memory` / PhysX `illegal memory access`

**现象**

- `Physics Device: cuda:0` / `GPU Pipeline: enabled` 后崩

**原因判断**

1. WSL2 对 PhysX GPU / CUDA pinned memory 支持差  
2. 曾用过新 Torch 与 Isaac Gym Preview 组合更不稳

**拟解决**

在 `climrs/run.py` 硬编码 `sys.argv` 增加：

```python
"--sim_device", "cpu",
"--pipeline", "cpu",
```

（策略网络仍可用 CUDA。）原生 Linux 4090 上 GPU PhysX 已可跑，本节主要针对 WSL。

---

### 9. `failed to preload CUDA lib` / WSL `libcuda.so`

**解决**

```bash
export LD_LIBRARY_PATH=$ISAACGYM_LIB:/usr/lib/wsl/lib:$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

---

### 10. 无显示器 / headless

`run.py` 里硬编码了 `sys.argv`，外面传 `--headless` 无效。在硬编码参数中加入 `"--headless"`：

```bash
python - << 'EOF'
from pathlib import Path
p = Path("climrs/run.py")
t = p.read_text()
if '"--headless"' not in t:
    t = t.replace('"--test",\n', '"--test",\n        "--headless",\n', 1)
    p.write_text(t)
    print("patched: added --headless")
else:
    print("already has --headless")
EOF
```

---

### 11. LLM：`LLM dev_revision not available` / 导入失败

**原因**

- `PYTHONPATH` 未含项目根与 `LLM/`（代码是 `from llm_utils...` 与 `from LLM.dev_revision...`）
- 缺依赖：`openai`、`backoff` 等
- `args.py` 缺 `API_KEY_R17B` / `API_URL_R17B`（`oracle_planner` 会从 `llm_module` 导入）

**配置 `LLM/llm_utils/args.py`（勿把真实 key 提交 git）**

```python
# Agent 会再拼 /v1/chat/completions，这里不要带 /v1
API_URL = "https://api.minimaxi.com"   # 不要写成 .../v1
API_KEY_CLIMRS = "<YOUR_KEY>"
API_URL_R17B = API_URL
API_KEY_R17B = API_KEY_CLIMRS
MODEL_SELECTION = "MiniMax-M3"
```

**验证导入与 API**

```bash
export PYTHONPATH=$CLIMRS_ROOT:$CLIMRS_ROOT/LLM:$CLIMRS_ROOT/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH

python -c "from LLM.dev_revision.arena import ArenaMultiAgent; print('LLM import OK')"

python - << 'EOF'
from LLM.llm_utils.llm_module import Agent
from LLM.llm_utils.args import API_URL, API_KEY_CLIMRS, MODEL_SELECTION
a = Agent(model=MODEL_SELECTION, api_url=API_URL, api_key=API_KEY_CLIMRS)
print(a.respond_once_all_args(
    messages=[{"role":"user","content":"只回复：ok"}],
    max_tokens=32, temperature=0))
EOF
```

---

### 12. LLM：`LLM planning failed: [Errno 2] ... './log/env0.txt'`

**原因**

- `LLM/dev_revision/LLM.py` 写日志到 `./log/{env}.txt`，目录不存在

**解决**

```bash
cd $CLIMRS_ROOT
mkdir -p log
python climrs/run.py
```

---

### 13. LLM：`No valid groups` / `Group execution failed - no valid actions` / 小车一直 idle

**现象**

- Oracle 已抽出正确指令：`Hello <mobile_car_3>(203): ... [move] ... [push] ...`
- 但随后反复出现：
  - `the first sentence is <THINK>...`
  - `No more things to do!`
  - `Oracle output: ... Group execution failed - no valid actions generated.`
  - 三辆车一直 `idle`

**原因（两层）**

1. **Agent 门闩**：`feedback_agent` 要求首句精确等于 `YES I CAN`；MiniMax-M3 先输出 `<think>` / 分析文字，进不了选动作分支。  
2. **`parse_answer` 把 `_` 换成空格**：`mobile_car_1` 对不上动作列表里的 `mobile_car_1`。  
3. 仅改 `LLM.py` 不够：`oracle_planner` / `feedback_agent` 各自调 `llm_module.Agent`，必须在 **`llm_module` 出口统一 strip**，并放宽 YES I CAN / 按 `[move]` 等 skill 匹配。

**解决**

见下方「服务器一键同步补丁」命令（改 `LLM/llm_utils/llm_module.py` + `LLM/dev_revision/llm_agents/feedback_agent.py`）。

成功标志：打印出具体 plan（如 `[move] <mobile_car_3> (203) ...`），而不再是连续 `No more things to do!`。

---

## `--test` 行为说明（动画“重复但不最优”）

| 现象 | 含义 |
|---|---|
| 反复刷 `reward: ... steps: 599` | 在循环评测 episode，不是训练 |
| `steps: 599` | 顶到 `episodeLength: 600` 超时结束 |
| 程序很久不退出 | `rl_games` 默认 `games_num` 很大（常约 2000）；`Ctrl+C` 可停 |
| RRT fail → default paths | 高层路径非最优，底层 Humanoid 策略仍在动 |
| 未开 LLM 时 | 只有底层策略 + RRT/默认路径，达不到论文完整闭环效果 |

少跑几局可在 train yaml 的 `params.config` 加：

```yaml
player:
  games_num: 5
```

---

## 可忽略的警告

| 警告 | 说明 |
|---|---|
| `No module named 'fbx'` | 不影响非 FBX 动作 |
| Gym / NumPy 2.0 deprecation | 先忽略 |
| URDF `No inertial data`（pybullet） | 用默认惯性，一般可跑 |
| `Not connected to PVD` | PhysX Visual Debugger，无关紧要 |
| `WARNING: LLM dev_revision not available` | 导入修好前可忽略；修后不应再出现 |
| Box bound precision lowered | gym spaces 常见提示 |

---

## 目录关系速查

### 原生 Linux

```text
/media/ubuntu/Student/gengzeyu/CLiMRS/     # CLIMRS_ROOT
├── climrs/run.py
├── Agent/                                 # 目录内链到 Agent_asset 子目录
│   ├── franka_description -> ../Agent_asset/franka_description
│   ├── Component_asset -> ../Agent_asset/Component_asset
│   └── Franka_agent.py
├── Agent_asset/
├── IsaacGymEnvs/.../tasks/amp/poselib/    # PYTHONPATH 指到 amp
├── LLM/                                   # PYTHONPATH 需含 CLiMRS 与 LLM
├── isaacgym/
└── log/                                   # mkdir -p log
```

### WSL（旧）

```text
/mnt/e/gengzeyu/CLiMRS/
├── IsaacGymEnvs/
└── CLiMRS/                        # CLIMRS_ROOT
    ├── Agent -> Agent_asset
    ├── Agent_asset/
    └── isaacgym/
```

---

## 进度状态（2026-07-28）

| 阶段 | WSL | 原生 Linux 4090 |
|---|---|---|
| poselib / LD_LIBRARY_PATH / isaacgym | ✅ | ✅ |
| rl-games==1.1.4 | ✅ | ✅ |
| 缺 carryobject 模块（可选导入） | — | ✅ 已绕过 |
| Agent / Franka URDF | ✅ | ✅（子目录软链） |
| RRT 2D 坐标 | — | ✅ 已 patch |
| nvrtc sm_89 / 禁用 JIT | — | ✅ |
| GPU PhysX 稳定 | ❌ WSL 卡点 | ✅ 可跑 |
| `--test` 出 reward | — | ✅ |
| MiniMax API 连通 | — | ✅ |
| LLM import + `log/` | — | ✅（需 `mkdir -p log`） |
| MiniMax `<think>` 干扰解析 | — | ✅ 需 strip（见第 13 节） |
| LLM 规划闭环效果 | 未充分验证 | 进行中（分组/动作解析） |

---

## 建议下次启动命令（原生 Linux）

```bash
conda activate climrs
cd /media/ubuntu/Student/gengzeyu/CLiMRS

export TORCH_CUDA_ARCH_LIST=8.6
export CLIMRS_ROOT=/media/ubuntu/Student/gengzeyu/CLiMRS
export LD_LIBRARY_PATH=$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
export PYTHONPATH=$CLIMRS_ROOT:$CLIMRS_ROOT/LLM:$CLIMRS_ROOT/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH

mkdir -p log
python climrs/run.py
```
