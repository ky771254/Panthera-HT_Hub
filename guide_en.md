# SDK Directory Guide

> This guide explains what each folder in the Panthera-HT SDK is for and where you should start.

## Overall Layout

```plaintext
Panthera-HT_SDK/
├── panthera_cpp/           ← Low-level C++ implementation (advanced users)
├── panthera_python/        ← Python control stack (the main entry for most users)
├── LICENSE                 ← Open-source license
└── README.md               ← Quick start overview
```

In short:

* `panthera_cpp` contains the low-level C++ driver and robot logic.
* `panthera_python` contains the Python-facing control interface and examples.
* Most users can stay inside `panthera_python`.

## panthera_python/ - Main Python Workspace

This is the directory you will use most of the time. All Python examples live here.

```plaintext
panthera_python/
├── scripts/                    ← Examples and learning entry point
├── robot_param/                ← Robot configuration files
├── Panthera-HT_description/    ← 3D model and URDF assets
├── motor_whl/                  ← Prebuilt motor driver wheels
├── images/                     ← Documentation images
├── src/                        ← Python binding source
├── requirements.txt            ← Python dependency list
├── README.md                   ← Python SDK usage guide
└── CMakeLists.txt              ← Build config for source builds
```

### scripts/ - Example Library

This folder contains the ready-to-run control examples, from basic inspection scripts to advanced trajectory and teleoperation demos.

```plaintext
scripts/
├── Panthera_lib/                              ← High-level control library
│   ├── Panthera.py                            ← Main robot control class
│   ├── recorder.py                            ← Trajectory record / replay helper
│   └── __init__.py                            ← Module init
│
├── 0_robot_get_state.py                       ← Read robot state first
├── 0_robot_set_zero.py                        ← Set the zero position
│
├── 1_Joint_PosVel_control.py                  ← Joint position + velocity control
├── 1_Joint_Vel_control.py                     ← Pure joint velocity control
├── 1_Joint_PD_control.py                      ← Low-level PD control
├── 1_moveJ_control.py                         ← Synchronized joint-space motion
├── 1_forward_kinematics_test.py               ← Forward kinematics test
├── 1_inverse_kinematics_test.py               ← Inverse kinematics test
│
├── 2_inv_PosVel_control.py                    ← Cartesian position control via IK
├── 2_gravity_compensation_control.py          ← Gravity compensation
├── 2_gravity_friction_compensation_control.py ← Gravity + friction compensation
├── 2_Jointimpendence_control_with_gra_pd.py   ← Joint impedance with gravity + PD
├── 2_Jointimpendence_control_with_gra_fri_pd.py ← Joint impedance with gravity + friction + PD
│
├── 3_interpolation_control_zeroVel.py         ← Polynomial interpolation, zero end velocity
├── 3_interpolation_control_nozeroVel.py       ← Polynomial interpolation, non-zero end velocity
├── 3_sin_trajectory_control.py                ← Sine trajectory tracking
├── 3_gravity_compensation_with_fk.py          ← Gravity compensation + FK display
│
├── 4_impedance_trajectory_control_with_gra_pd.py ← Trajectory-level impedance control
│
├── 5_record_trajectory.py                     ← Teach by dragging and record
├── 5_replay_trajectory.py                     ← Replay a recorded trajectory
├── 5_teleop_control.py                        ← Master-slave teleoperation
│
├── 6_moveL_pos_control.py                     ← Linear Cartesian motion, position mode
├── 6_moveL_rotate_control.py                  ← Linear Cartesian motion, rotation mode
│
├── 7_keyboard_cartesian_pos_control.py        ← Keyboard Cartesian position control
├── 7_keyboard_cartesian_vel_control.py        ← Keyboard Cartesian velocity control
│
└── motor_example/                             ← Low-level single-motor examples
    ├── 01_motor_get_status.py
    ├── 02_position_control.py
    ├── 03_velocity_control.py
    ├── 04_torque_control.py
    ├── 05_voltage_control.py
    ├── 06_current_control.py
    ├── 07_pos_vel_maxtorque_control.py
    ├── 08_pos_vel_torque_kp_kd_control.py
    ├── 09_set_zero.py
    ├── motor_control.py
    └── motor_README.md
```

Recommended learning path:

1. Start with `0_robot_get_state.py` to confirm the hardware connection is healthy.
2. Learn the basic motion APIs with the `1_` examples.
3. Move on to compensation and interpolation with the `2_` and `3_` examples.
4. Use the `5_`, `6_`, and `7_` examples as application references.
5. Do not directly run the `motor_example/` scripts unless you are debugging a specific motor.

`Panthera_lib/` is the high-level wrapper used by almost every example. In day-to-day usage, `Panthera.py` is the core file you will build on.

#### Gripper Control

The gripper is the seventh motor in the chain. It is managed through `Panthera_lib` with an API style that matches the joint control interface.

```yaml
gripper_limits:
  lower: 0.0   # fully closed (rad)
  upper: 2.0   # fully open (rad)
```

Common APIs:

| Method | Description |
| --- | --- |
| `gripper_open(pos=1.6, vel=0.5, max_tqu=0.5)` | Open the gripper |
| `gripper_close(pos=0.0, vel=0.5, max_tqu=0.5)` | Close the gripper |
| `gripper_control(pos, vel, max_tqu)` | Precise position / velocity / max torque control |
| `gripper_control_MIT(pos, vel, tqe, kp, kd)` | MIT-style five-parameter control |
| `get_current_pos_gripper()` | Read current gripper position |
| `get_current_vel_gripper()` | Read current gripper velocity |
| `get_current_torque_gripper()` | Read current gripper torque |

Typical usage:

```python
from Panthera_lib import Panthera

robot = Panthera("../robot_param/Leader.yaml")

robot.gripper_open()
robot.gripper_close()
robot.gripper_control(1.0, 0.5, 0.5)
```

Commands outside `[0.0, 2.0]` are rejected for safety.

### robot_param/ - Robot Configuration

This directory stores robot-level configuration, such as joint limits, torque limits, and motor IDs.

```plaintext
robot_param/
├── Leader.yaml                 ← Main arm config
├── Follower.yaml               ← Follower arm config
└── motor_param/                ← Low-level motor config
    ├── 6dof_Panthera_params_leader.yaml
    ├── 6dof_Panthera_params_follower.yaml
    ├── motor_1.yaml
    ├── motor_6.yaml
    └── robot_config.yaml
```

Example:

```yaml
robot:
  name: "Panthera-HT"
  joint_limits:
    lower: [-2.4, 0.0, 0.0, -1.6, -1.7, -2.5]
    upper: [2.4, 3.2, 4.0, 1.6, 1.7, 2.5]
  max_torque: [21, 36, 36, 21, 10, 10]
  velocity_limits: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
  acceleration_limits: [2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
```

When should you edit these files:

* For a single-arm setup, make sure the correct `end_effector_link` is used for the arm model you are running.
* For a dual-arm setup, the master arm should use `Leader.yaml` and the follower arm should use `Follower.yaml`.
* Most users do not need to edit these files unless they are adjusting limits or hardware-specific parameters.

### Panthera-HT_description/ - 3D Model and URDF Assets

This directory stores the URDF robot model and the mesh assets used by kinematics, dynamics, and visualization tooling.

```plaintext
Panthera-HT_description/
├── urdf/
│   ├── Panthera-HT_description_leader.urdf
│   └── Panthera-HT_description_follower.urdf
├── meshes/
│   ├── base_link.stl
│   ├── link1.stl
│   └── ...
├── config/
└── launch/
```

You usually do not need to edit this folder unless you are working with visualization, model geometry, or robot description data.

### motor_whl/ - Prebuilt Motor Driver Wheels

This folder contains prebuilt Python wheels for the motor communication layer.

```plaintext
motor_whl/
├── hightorque_robot-1.2.0-cp39-cp39-linux_x86_64.whl
├── hightorque_robot-1.2.0-cp310-cp310-linux_x86_64.whl
├── hightorque_robot-1.2.0-cp311-cp311-linux_x86_64.whl
├── hightorque_robot-1.2.0-cp312-cp312-linux_x86_64.whl
├── hightorque_robot-1.0.0-cp39-cp39-linux_aarch64.whl
├── hightorque_robot-1.0.0-cp310-cp310-linux_aarch64.whl
├── hightorque_robot-1.0.0-cp311-cp311-linux_aarch64.whl
└── hightorque_robot-1.0.0-cp312-cp312-linux_aarch64.whl
```

Install the wheel that matches your Python version and CPU architecture.

### images/ - Documentation Assets

This folder stores the images used in the docs and README files.

### src/ - Python Binding Source

This is the pybind11 bridge layer between the C++ implementation and the Python package.

### Other Files

| File | Purpose |
| --- | --- |
| `requirements.txt` | Python dependencies |
| `README.md` | Python SDK guide |
| `CMakeLists.txt` | Build config for source builds |
| `setup.py` | Python package install script |
| `pyproject.toml` | Python project config |

## panthera_cpp/ - Lower-Level C++ Stack

This is the low-level C++ implementation that handles device communication and the core robot model logic.

```plaintext
panthera_cpp/
├── motor_cpp/                  ← Motor communication layer
├── robot_cpp/                  ← Robot control layer
└── README.md                   ← C++ SDK guide
```

Python users usually do not need to modify this part directly.

### motor_cpp/ - Motor Driver Layer

This layer communicates with motors over CAN and exposes the low-level control modes.

Core responsibilities:

* CAN communication
* Motor state feedback
* Position / velocity / torque / MIT control modes
* Multiple motor model support

### robot_cpp/ - Robot Control Layer

This layer builds on the motor driver layer and provides kinematics, dynamics, gravity compensation, Jacobians, and trajectory logic.

## Root-Level Files

```plaintext
Panthera-HT_SDK/
├── LICENSE                     ← MIT license
└── README.md                   ← Project overview and quick start
```

## Quick Navigation: Where Should I Start?

### Scenario 1: I am a Python user and want to get started quickly

Focus on:

* `panthera_python/scripts/`
* `panthera_python/README.md`
* `panthera_python/robot_param/`

### Scenario 2: I want to understand how the SDK works internally

Recommended reading order:

1. `panthera_python/scripts/Panthera_lib/Panthera.py`
2. `panthera_cpp/motor_cpp`
3. `panthera_cpp/robot_cpp`

### Scenario 3: I want to change robot parameters

Start with:

* `robot_param/Leader.yaml`
* `robot_param/Follower.yaml`
* `robot_param/motor_param/`

### Scenario 4: I want to develop in C++

Focus on:

* `panthera_cpp/motor_cpp`
* `panthera_cpp/robot_cpp`
* `panthera_cpp/README.md`

## Dependency Map

```plaintext
Your Python script
    ↓ import
Panthera_lib
    ↓ import
hightorque_robot
    ↓ pybind11 binding
panthera_cpp/motor_cpp
    ↓ CAN communication
Robot hardware
```

## FAQ

Q1: Do I need to compile the C++ code if I only want to use Python?  
A: Usually no. Install the matching wheel from `motor_whl/`.

Q2: What is the difference between `Panthera_lib` and `hightorque_robot`?  
A: `hightorque_robot` is the low-level Python binding, while `Panthera_lib` is the high-level SDK wrapper used by the examples.

Q3: When should I use `Leader.yaml` vs `Follower.yaml`?  
A: Use the file that matches the arm role and end-effector definition in your setup.
