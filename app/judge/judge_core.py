import docker
import time

client = docker.from_env()


def docker_judge(code: str, input_data: str, expected_output: str, language: str, timeout=5) -> str:
    try:
        # 根据语言选择镜像和命令
        image_map = {
            "python": ("python:3.9-slim", ["python", "-c", code]),
            "cpp": ("gcc:latest", f"bash -c 'echo \"{code}\" > main.cpp && g++ main.cpp -o main && ./main'"),
            "java": ("openjdk:11", f"bash -c 'echo \"{code}\" > Main.java && javac Main.java && java Main'")
        }

        image, command = image_map[language]
        if language != "python":
            command = ["sh", "-c", command]

        # 创建容器
        container = client.containers.run(
            image=image,
            command=command,
            stdin_open=True,
            detach=True,
            network_mode='none',
            mem_limit='512m',  # C++/Java需要更多内存
            cpu_period=100000,
            cpu_quota=50000
        )

        # 发送输入数据
        socket = container.attach_socket(params={'stdin': 1, 'stream': 1})
        socket.sendall(input_data.encode() + b'\n')  # 修改这里
        socket.close()

        # 等待执行完成
        start_time = time.time()
        while container.status != 'exited':
            if time.time() - start_time > timeout:
                container.stop()
                return "Time Limit Exceeded"
            time.sleep(0.1)
            container.reload()

        # 获取输出
        logs = container.logs(stdout=True, stderr=False).decode().strip()
        container.remove(force=True)

        return "Accepted" if logs == expected_output.strip() else f"Wrong Answer (Expected: {expected_output}, Got: {logs})"

    except Exception as e:
        return f"Error: {str(e)}"