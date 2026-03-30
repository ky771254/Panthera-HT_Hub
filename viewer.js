import * as THREE from "./vendor/three/three.module.js";
import { OrbitControls } from "./vendor/three/examples/jsm/controls/OrbitControls.js";

const WORLD_UP = new THREE.Vector3(0, 0, 1);
const DEFAULT_JOINT_SPEED_DEG = 180;
const MIN_JOINT_SPEED_DEG = 30;
const MAX_JOINT_SPEED_DEG = 360;
const DEFAULT_JOINTS = [
    { name: "joint1", axis: [0, 0, 1], limit: { lower: -2.4, upper: 2.4 } },
    { name: "joint2", axis: [0, 1, 0], limit: { lower: 0.0, upper: 3.2 } },
    { name: "joint3", axis: [0, -1, 0], limit: { lower: 0.0, upper: 4.0 } },
    { name: "joint4", axis: [0, -1, 0], limit: { lower: -1.6, upper: 1.6 } },
    { name: "joint5", axis: [0, 0, -1], limit: { lower: -1.7, upper: 1.7 } },
    { name: "joint6", axis: [1, 0, 0], limit: { lower: -2.5, upper: 2.5 } },
];
const ROBOT_DESCRIPTION = createRobotDescription();

const state = {
    jointStates: new Map(),
    sliderMap: new Map(),
    renderer: null,
    camera: null,
    controls: null,
    scene: null,
    robotRoot: null,
    baseCameraPosition: new THREE.Vector3(),
    baseCameraTarget: new THREE.Vector3(),
    lastFrameTime: 0,
    jointSpeed: THREE.MathUtils.degToRad(DEFAULT_JOINT_SPEED_DEG),
};

const canvas = document.getElementById("viewer-canvas");
const jointControls = document.getElementById("joint-controls");
const statusEl = document.getElementById("viewer-status");
const resetButton = document.getElementById("viewer-reset");
const homeButton = document.getElementById("viewer-home");
const toggleButton = document.getElementById("viewer-toggle");
const stage = document.getElementById("viewer-stage");
const speedSlider = document.getElementById("joint-speed");
const speedValueEl = document.getElementById("joint-speed-value");
const container = canvas?.parentElement;

if (canvas && jointControls && statusEl && resetButton && homeButton && toggleButton && stage && container) {
    initViewer().catch((error) => {
        console.error(error);
        setStatus("Viewer 初始化失败，请检查浏览器控制台。", false);
    });
}

async function initViewer() {
    setupScene();
    setViewerActive(false);
    setStatus("正在初始化模型 ...", true);
    createJointControls(ROBOT_DESCRIPTION.joints);
    setViewerActive(false);
    setStatus("正在加载 STL 模型 ...", true);

    try {
        state.robotRoot = await buildRobot(ROBOT_DESCRIPTION);
        state.scene.add(state.robotRoot);
        frameRobot(state.robotRoot);
        setStatus("模型已加载，可以拖动关节和视角。", true);
        window.setTimeout(() => setStatus("", false), 2200);
    } catch (error) {
        console.error(error);
        const message = location.protocol === "file:"
            ? "模型加载失败：请通过 HTTP 服务访问页面，不能直接用 file:// 打开。"
            : `模型加载失败：${error.message || "请检查浏览器控制台。"}`;
        setStatus(message, true);
    }

    resetButton.addEventListener("click", resetPose);
    homeButton.addEventListener("click", resetCamera);
    toggleButton.addEventListener("click", () => setViewerActive(stage.classList.contains("is-blocked")));
    if (speedSlider) {
        speedSlider.addEventListener("input", () => {
            setJointSpeedDegrees(Number(speedSlider.value));
        });
        setJointSpeedDegrees(Number(speedSlider.value) || DEFAULT_JOINT_SPEED_DEG);
    }
    window.addEventListener("resize", handleResize);
    handleResize();
    animate();
}

function setupScene() {
    const renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f8f8);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
    camera.up.copy(WORLD_UP);
    camera.position.set(1.4, 0.95, 1.2);

    const controls = new OrbitControls(camera, canvas);
    controls.enabled = false;
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0, 0.28);
    controls.minDistance = 0.35;
    controls.maxDistance = 4.5;

    const hemisphereLight = new THREE.HemisphereLight(0xffffff, 0xebebeb, 1.05);
    hemisphereLight.position.copy(WORLD_UP);
    scene.add(hemisphereLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
    keyLight.position.set(2.2, 2.1, 1.4);
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xffffff, 0.45);
    fillLight.position.set(-1.4, 1.2, -1.1);
    scene.add(fillLight);

    const grid = new THREE.GridHelper(1.8, 18, 0xd7d7d7, 0xe8e8e8);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = 0;
    scene.add(grid);

    state.renderer = renderer;  
    state.scene = scene;
    state.camera = camera;
    state.controls = controls;
}

function createRobotDescription() {
    const links = new Map();
    [
        ["base_link", "meshes/base_link.STL"],
        ["link1", "meshes/link1.STL"],
        ["link2", "meshes/link2.STL"],
        ["link3", "meshes/link3.STL"],
        ["link4", "meshes/link4.STL"],
        ["link5", "meshes/link5.STL"],
        ["link6", "meshes/link6.STL"],
        ["tool_link", ""],
    ].forEach(([name, mesh]) => {
        links.set(name, {
            name,
            visuals: mesh
                ? [
                    {
                        xyz: [0, 0, 0],
                        rpy: [0, 0, 0],
                        mesh,
                        color: "0.752941176470588 0.752941176470588 0.752941176470588 1",
                    },
                ]
                : [],
        });
    });

    return {
        links,
        joints: [
            {
                name: "joint1",
                type: "revolute",
                parent: "base_link",
                child: "link1",
                xyz: [0, 0, 0.0584],
                rpy: [0, 0, 0],
                axis: [0, 0, 1],
                limit: { lower: -2.4, upper: 2.4 },
            },
            {
                name: "joint2",
                type: "revolute",
                parent: "link1",
                child: "link2",
                xyz: [0.018199, 0, 0.053],
                rpy: [0, 0, 0],
                axis: [0, 1, 0],
                limit: { lower: 0, upper: 3.2 },
            },
            {
                name: "joint3",
                type: "revolute",
                parent: "link2",
                child: "link3",
                xyz: [-0.26, 0, 0],
                rpy: [0, 0, 0],
                axis: [0, -1, 0],
                limit: { lower: 0, upper: 4.0 },
            },
            {
                name: "joint4",
                type: "revolute",
                parent: "link3",
                child: "link4",
                xyz: [0.23, 0, 0.06],
                rpy: [0, 0, 0],
                axis: [0, -1, 0],
                limit: { lower: -1.6, upper: 1.6 },
            },
            {
                name: "joint5",
                type: "revolute",
                parent: "link4",
                child: "link5",
                xyz: [0.07, 0, 0.036319],
                rpy: [0, 0, 0],
                axis: [0, 0, -1],
                limit: { lower: -1.7, upper: 1.7 },
            },
            {
                name: "joint6",
                type: "revolute",
                parent: "link5",
                child: "link6",
                xyz: [0.02345, 0, -0.039],
                rpy: [0, 0, 0],
                axis: [1, 0, 0],
                limit: { lower: -2.5, upper: 2.5 },
            },
            {
                name: "tool_joint",
                type: "fixed",
                parent: "link6",
                child: "tool_link",
                xyz: [0.165, 0, 0],
                rpy: [0, 0, 0],
                axis: [0, 0, 1],
                limit: { lower: 0, upper: 0 },
            },
        ],
        rootLink: "base_link",
    };
}

function createJointControls(joints) {
    state.jointStates.clear();
    state.sliderMap.clear();
    jointControls.innerHTML = "";

    const sourceJoints = joints.filter((joint) => joint.type !== "fixed");
    const visibleJoints = sourceJoints.length ? sourceJoints : DEFAULT_JOINTS;
    const orderedJoints = orderJointControlsForColumns(visibleJoints);

    orderedJoints.forEach((joint) => {
        const card = document.createElement("div");
        card.className = "joint-card";

        const header = document.createElement("div");
        header.className = "joint-card-header";

        const name = document.createElement("span");
        name.className = "joint-name";
        name.textContent = joint.name;

        const value = document.createElement("span");
        value.className = "joint-value";
        value.textContent = formatDegrees(0);

        header.append(name, value);

        const slider = document.createElement("input");
        slider.className = "joint-slider";
        slider.type = "range";
        slider.min = String(radiansToDegrees(joint.limit.lower));
        slider.max = String(radiansToDegrees(joint.limit.upper));
        slider.step = "0.1";
        slider.value = "0";
        slider.setAttribute("aria-label", joint.name);

        const limits = document.createElement("div");
        limits.className = "joint-limits";
        limits.innerHTML = `<span>${formatDegrees(joint.limit.lower)}</span><span>${formatDegrees(joint.limit.upper)}</span>`;

        slider.addEventListener("input", () => {
            const radians = degreesToRadians(Number(slider.value));
            setJointTarget(joint.name, radians);
        });

        slider.addEventListener("pointerdown", () => card.classList.add("active"));
        slider.addEventListener("pointerup", () => card.classList.remove("active"));
        slider.addEventListener("blur", () => card.classList.remove("active"));

        card.append(header, slider, limits);
        jointControls.appendChild(card);

        state.sliderMap.set(joint.name, { slider, value, card });
        state.jointStates.set(joint.name, {
            value: 0,
            target: 0,
            lower: joint.limit.lower,
            upper: joint.limit.upper,
            axis: new THREE.Vector3(...joint.axis).normalize(),
            pivot: null,
        });
    });
}

function orderJointControlsForColumns(joints) {
    const byName = new Map(joints.map((joint) => [joint.name, joint]));
    const ordered = [];
    const preferredOrder = ["joint1", "joint3", "joint5", "joint2", "joint4", "joint6"];

    preferredOrder.forEach((name) => {
        const joint = byName.get(name);
        if (joint) {
            ordered.push(joint);
            byName.delete(name);
        }
    });

    // Keep any non-standard joints visible after the primary six.
    byName.forEach((joint) => ordered.push(joint));
    return ordered;
}

function setJointSpeedDegrees(rawValue) {
    const clamped = THREE.MathUtils.clamp(rawValue, MIN_JOINT_SPEED_DEG, MAX_JOINT_SPEED_DEG);
    state.jointSpeed = THREE.MathUtils.degToRad(clamped);

    if (speedValueEl) {
        speedValueEl.textContent = `${Math.round(clamped)}°/s`;
    }

    if (speedSlider && Number(speedSlider.value) !== Number(clamped.toFixed(0))) {
        speedSlider.value = String(Math.round(clamped));
    }
}

async function buildRobot(description) {
    const jointChildren = new Map();
    description.joints.forEach((joint) => {
        if (!jointChildren.has(joint.parent)) {
            jointChildren.set(joint.parent, []);
        }
        jointChildren.get(joint.parent).push(joint);
    });

    const meshTasks = [];

    const createLinkGroup = (linkName) => {
        const link = description.links.get(linkName);
        const linkGroup = new THREE.Group();
        linkGroup.name = linkName;

        if (link?.visuals?.length) {
            link.visuals.forEach((visual) => {
                const visualGroup = new THREE.Group();
                visualGroup.position.set(...visual.xyz);
                visualGroup.rotation.set(...visual.rpy, "XYZ");
                linkGroup.add(visualGroup);

                if (visual.mesh) {
                    const task = loadStlGeometry(visual.mesh).then((geometry) => {
                        geometry.computeVertexNormals();
                        const mesh = new THREE.Mesh(
                            geometry,
                            new THREE.MeshStandardMaterial({
                                color: parseColor(visual.color),
                                metalness: 0.16,
                                roughness: 0.58,
                            }),
                        );
                        mesh.castShadow = false;
                        mesh.receiveShadow = true;
                        visualGroup.add(mesh);
                    });
                    meshTasks.push(task);
                }
            });
        }

        const children = jointChildren.get(linkName) || [];
        children.forEach((joint) => {
            const jointFrame = new THREE.Group();
            jointFrame.name = `${joint.name}-frame`;
            jointFrame.position.set(...joint.xyz);
            jointFrame.rotation.set(...joint.rpy, "XYZ");

            const jointPivot = new THREE.Group();
            jointPivot.name = `${joint.name}-pivot`;
            jointFrame.add(jointPivot);
            jointPivot.add(createLinkGroup(joint.child));
            linkGroup.add(jointFrame);

            if (joint.type !== "fixed") {
                const jointState = state.jointStates.get(joint.name);
                if (jointState) {
                    jointState.axis = new THREE.Vector3(...joint.axis).normalize();
                    jointState.pivot = jointPivot;
                    applyJointValue(joint.name, jointState.value, { setTarget: true });
                }
            }
        });

        return linkGroup;
    };

    const robotRoot = createLinkGroup(description.rootLink);
    await Promise.all(meshTasks);
    return robotRoot;
}

function setJointTarget(jointName, rawValue, options = {}) {
    const jointState = state.jointStates.get(jointName);
    if (!jointState) {
        return;
    }

    const clamped = THREE.MathUtils.clamp(rawValue, jointState.lower, jointState.upper);
    jointState.target = clamped;

    if (options.immediate) {
        applyJointValue(jointName, clamped, { syncUi: false, setTarget: true });
    }

    if (options.syncUi !== false) {
        updateJointUi(jointName, clamped);
    }
}

function applyJointValue(jointName, rawValue, options = {}) {
    const jointState = state.jointStates.get(jointName);
    if (!jointState) {
        return;
    }

    const clamped = THREE.MathUtils.clamp(rawValue, jointState.lower, jointState.upper);
    jointState.value = clamped;
    if (options.setTarget) {
        jointState.target = clamped;
    }

    if (jointState.pivot) {
        jointState.pivot.quaternion.setFromAxisAngle(jointState.axis, clamped);
    }

    if (options.syncUi !== false) {
        updateJointUi(jointName, clamped);
    }
}

function resetPose() {
    state.jointStates.forEach((jointState, jointName) => {
        const nextValue = THREE.MathUtils.clamp(0, jointState.lower, jointState.upper);
        setJointTarget(jointName, nextValue);
    });
}

function frameRobot(robotRoot) {
    const bounds = new THREE.Box3().setFromObject(robotRoot);
    const size = bounds.getSize(new THREE.Vector3());
    const center = bounds.getCenter(new THREE.Vector3());
    const radius = Math.max(size.x, size.y, size.z) * 0.9 || 0.7;

    state.controls.target.copy(center);
    state.baseCameraTarget.copy(center);

    const cameraOffset = new THREE.Vector3(radius * 1.0, radius * 0.9, radius * 0.85);
    const cameraPosition = center.clone().add(cameraOffset);
    state.camera.position.copy(cameraPosition);
    state.baseCameraPosition.copy(cameraPosition);
    state.camera.near = Math.max(radius / 120, 0.01);
    state.camera.far = Math.max(radius * 20, 10);
    state.camera.updateProjectionMatrix();
    state.controls.update();
}

function resetCamera() {
    state.camera.position.copy(state.baseCameraPosition);
    state.controls.target.copy(state.baseCameraTarget);
    state.controls.update();
}

function setViewerActive(isActive) {
    stage.classList.toggle("is-blocked", !isActive);
    canvas.style.pointerEvents = isActive ? "auto" : "none";
    state.controls.enabled = isActive;
    resetButton.disabled = !isActive;
    homeButton.disabled = !isActive;

    state.sliderMap.forEach(({ slider }) => {
        slider.disabled = !isActive;
    });
    if (speedSlider) {
        speedSlider.disabled = !isActive;
    }

    toggleButton.textContent = isActive ? "STOP" : "START";
    toggleButton.classList.toggle("toggle-start", !isActive);
    toggleButton.classList.toggle("toggle-stop", isActive);
    toggleButton.setAttribute("aria-pressed", String(isActive));
}

function handleResize() {
    const rect = container.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) {
        return;
    }

    state.camera.aspect = rect.width / rect.height;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(rect.width, rect.height, false);
}

function animate(time) {
    requestAnimationFrame(animate);
    updateJointMotion(time);
    state.controls.update();
    state.renderer.render(state.scene, state.camera);
}

function setStatus(message, visible) {
    statusEl.textContent = message;
    statusEl.classList.toggle("hidden", !visible);
}

function parseTriple(value = "0 0 0") {
    return value
        .trim()
        .split(/\s+/)
        .slice(0, 3)
        .map((entry) => Number(entry || 0));
}

function parseColor(rgba) {
    const channels = rgba
        .trim()
        .split(/\s+/)
        .slice(0, 3)
        .map((value) => Number(value));

    return new THREE.Color(channels[0] || 0.75, channels[1] || 0.75, channels[2] || 0.75);
}

function radiansToDegrees(value) {
    return THREE.MathUtils.radToDeg(value);
}

function degreesToRadians(value) {
    return THREE.MathUtils.degToRad(value);
}

function formatDegrees(radians) {
    const degrees = radiansToDegrees(radians);
    return `${degrees >= 0 ? "+" : ""}${degrees.toFixed(1)}°`;
}

function updateJointUi(jointName, radians) {
    const controls = state.sliderMap.get(jointName);
    if (!controls) {
        return;
    }
    const degreeValue = radiansToDegrees(radians);
    if (Number(controls.slider.value) !== Number(degreeValue.toFixed(1))) {
        controls.slider.value = degreeValue.toFixed(1);
    }
    controls.value.textContent = formatDegrees(radians);
}

function updateJointMotion(time) {
    if (!Number.isFinite(time)) {
        return;
    }

    if (!state.lastFrameTime) {
        state.lastFrameTime = time;
        return;
    }

    const deltaSeconds = Math.min((time - state.lastFrameTime) / 1000, 0.05);
    state.lastFrameTime = time;

    const speed = Number.isFinite(state.jointSpeed) ? state.jointSpeed : THREE.MathUtils.degToRad(DEFAULT_JOINT_SPEED_DEG);
    const maxStep = speed * deltaSeconds;
    if (maxStep <= 0) {
        return;
    }

    state.jointStates.forEach((jointState, jointName) => {
        const target = Number.isFinite(jointState.target) ? jointState.target : jointState.value;
        const delta = target - jointState.value;
        if (Math.abs(delta) <= maxStep) {
            if (delta !== 0) {
                applyJointValue(jointName, target, { syncUi: false, setTarget: false });
            }
            return;
        }

        const nextValue = jointState.value + Math.sign(delta) * maxStep;
        applyJointValue(jointName, nextValue, { syncUi: false, setTarget: false });
    });
}

async function loadStlGeometry(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Unable to fetch STL: ${url} (${response.status})`);
    }

    const arrayBuffer = await response.arrayBuffer();
    return parseStlGeometry(arrayBuffer);
}

function parseStlGeometry(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    const faceCount = view.getUint32(80, true);
    const expectedBinaryLength = 84 + faceCount * 50;

    if (expectedBinaryLength === arrayBuffer.byteLength) {
        return parseBinaryStl(view, faceCount);
    }

    const text = new TextDecoder().decode(arrayBuffer);
    return parseAsciiStl(text);
}

function parseBinaryStl(view, faceCount) {
    const positions = new Float32Array(faceCount * 9);
    const normals = new Float32Array(faceCount * 9);
    let offset = 84;

    for (let faceIndex = 0; faceIndex < faceCount; faceIndex += 1) {
        const normal = [
            view.getFloat32(offset, true),
            view.getFloat32(offset + 4, true),
            view.getFloat32(offset + 8, true),
        ];
        offset += 12;

        for (let vertexIndex = 0; vertexIndex < 3; vertexIndex += 1) {
            const attributeIndex = faceIndex * 9 + vertexIndex * 3;
            positions[attributeIndex] = view.getFloat32(offset, true);
            positions[attributeIndex + 1] = view.getFloat32(offset + 4, true);
            positions[attributeIndex + 2] = view.getFloat32(offset + 8, true);

            normals[attributeIndex] = normal[0];
            normals[attributeIndex + 1] = normal[1];
            normals[attributeIndex + 2] = normal[2];
            offset += 12;
        }

        offset += 2;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
    return geometry;
}

function parseAsciiStl(text) {
    const positions = [];
    const normals = [];
    const pattern = /facet\s+normal\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)[\s\S]*?outer\s+loop[\s\S]*?vertex\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)[\s\S]*?vertex\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)[\s\S]*?vertex\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)[\s\S]*?endloop[\s\S]*?endfacet/g;
    let match = pattern.exec(text);

    while (match) {
        const values = match.slice(1).map(Number);
        const normal = values.slice(0, 3);
        const vertices = values.slice(3);

        for (let index = 0; index < 9; index += 3) {
            positions.push(vertices[index], vertices[index + 1], vertices[index + 2]);
            normals.push(normal[0], normal[1], normal[2]);
        }

        match = pattern.exec(text);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
    return geometry;
}
