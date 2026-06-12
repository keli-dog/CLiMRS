# Leveraging Adaptive Group Negotiation for Heterogeneous Multi-Robot Collaboration with Large Language Models

<div align="center">


</div>


<div style="text-align: center;">
    <img src="teaser/teaser.png" alt="Teaser" width=100% >
</div>



## Installation

Download Isaac Gym from [website](https://developer.nvidia.com/isaac-gym), or using CLI commands:

```bash
wget https://developer.nvidia.com/isaac-gym-preview-4
tar -xvzf isaac-gym-preview-4
```

Create conda environment:

```bash
conda create -n climrs python=3.8
conda activate climrs
```

Install IsaacGym wrappers for Python:

```bash
pip install -e isaacgym/python
```

Install other dependencies:

```bash
pip install -r requirements.txt
```
如果遇到如下错误：

```text
ImportError: libpython3.8m.so.1.0: cannot open shared object file: No such file or directory
ImportError: libpython3.8.so.1.0: cannot open shared object file: No such file or directory
```

需要设置 `LD_LIBRARY_PATH`。其中 `<CLIMRS_ROOT>` 表示包含 `climrs/run.py` 的 CLiMRS 项目目录，`<CONDA_PREFIX>` 表示当前激活的 conda 环境路径。

```bash
export LD_LIBRARY_PATH=<CLIMRS_ROOT>:<CONDA_PREFIX>/lib:$LD_LIBRARY_PATH
```

也可以显式设置：

```bash
export CLIMRS_ROOT=/path/to/CLiMRS/CLiMRS
export LD_LIBRARY_PATH=$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

如果需要永久生效，可以写入 `~/.bashrc`：

```bash
echo 'export LD_LIBRARY_PATH=/path/to/CLiMRS/CLiMRS:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc
```

### IsaacGymEnvs 和 PoseLib 配置

本项目使用 NVIDIA IsaacGymEnvs 中自带的 `PoseLib`。请先将 IsaacGymEnvs 放在 CLiMRS 项目旁边，例如：

```bash
cd /path/to/CLiMRS
git clone git@github.com:NVIDIA-Omniverse/IsaacGymEnvs.git
```

如果使用 SSH clone 时出现 OpenSSL mismatch，例如：

```text
OpenSSL version mismatch
```

请先更新 conda 中的 `git` 和 `openssl`：

```bash
conda install -c conda-forge git openssl
```

克隆完成后，可以先查找 `poselib` 的位置：

```bash
find /path/to/CLiMRS/IsaacGymEnvs -maxdepth 6 -iname "*poselib*"
```

通常可以找到类似下面的路径：

```text
/path/to/CLiMRS/IsaacGymEnvs/isaacgymenvs/tasks/amp/poselib
/path/to/CLiMRS/IsaacGymEnvs/isaacgymenvs/tasks/amp/poselib/poselib
```

本项目需要的是外层 `poselib` 所在目录的上一级，也就是：

```text
/path/to/CLiMRS/IsaacGymEnvs/isaacgymenvs/tasks/amp
```

因此需要将该目录加入 `PYTHONPATH`：

```bash
export PYTHONPATH=/path/to/CLiMRS/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH
```

或者相对于 CLiMRS 项目目录表示为：

```bash
export PYTHONPATH=<CLIMRS_ROOT>/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH
```

注意：不要在 `IsaacGymEnvs/isaacgymenvs/tasks/amp/poselib` 目录中执行 `pip install -e .`，因为该目录通常不包含 `setup.py` 或 `pyproject.toml`。

验证 PoseLib 是否能正确导入：

```bash
python -c "from poselib.poselib.skeleton.skeleton3d import SkeletonMotion, SkeletonState; print('poselib ok')"
```

如果输出：

```text
poselib ok
```

说明 PoseLib 配置成功。

如果需要永久生效，可以将 `PYTHONPATH` 写入 `~/.bashrc`：

```bash
echo 'export PYTHONPATH=/path/to/CLiMRS/IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc
```

一个典型的环境变量配置如下：

```bash
export CLIMRS_ROOT=/path/to/CLiMRS/CLiMRS
export LD_LIBRARY_PATH=$CLIMRS_ROOT:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
export PYTHONPATH=$CLIMRS_ROOT/../IsaacGymEnvs/isaacgymenvs/tasks/amp:$PYTHONPATH
python climrs/run.py
```

请根据你的实际安装位置修改 `/path/to/CLiMRS/CLiMRS` 和 IsaacGymEnvs 路径。

## Commands

### Reproduce Results for our Paper


```bash
conda activate climrs
python climrs/run.py
```
