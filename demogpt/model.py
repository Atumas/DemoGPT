import os
import sys
from time import sleep

import autopep8
from tqdm import trange

from demogpt.chains.chains import Chains
from demogpt.chains.task_chains import TaskChains
from demogpt.utils import getCodeSnippet, getFunctionNames, init


class DemoGPT:
    def __init__(
        self,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        model_name="gpt-3.5-turbo-0613",
        max_steps=10,
        openai_api_base="",
    ):
        assert len(
            openai_api_key.strip()
        ), "Either give openai_api_key as an argument or put it in the environment variable"
        self.model_name = model_name
        self.openai_api_key = openai_api_key
        self.max_steps = max_steps  # max iteration for refining the model purpose
        self.openai_api_base = openai_api_base
        Chains.setLlm(
            self.model_name, self.openai_api_key, openai_api_base=self.openai_api_base
        )
        TaskChains.setLlm(
            self.model_name, self.openai_api_key, openai_api_base=self.openai_api_base
        )
        self.FAIL_MESSAGE = """🚀✨ Impressive! While DemoGPT can handle a galaxy of app ideas, 
        you've shot for the stars with a unique one. We're ramping up our engines to meet such visionary requests. 
        Give us a little time, and we'll be right there with you.\n\n📧
        Care to leave your email? We'll notify you when we're ready for this stellar journey!"""

    def setModel(self, model_name):
        self.model_name = model_name
        Chains.setLlm(
            self.model_name, self.openai_api_key, openai_api_base=self.openai_api_base
        )
        TaskChains.setLlm(
            self.model_name, self.openai_api_key, openai_api_base=self.openai_api_base
        )

    def __repr__(self) -> str:
        return f"DemoGPT(model_name='{self.model_name}',max_steps={self.max_steps})"

    def __call__(
        self,
        instruction="Create a translation system that converts English to French",
        title="",
    ):

        yield {
            "stage": "system_inputs",
            "completed": False,
            "percentage": 0,
            "done": False,
            "message": "System inputs are being detected...",
            "failed": False,
        }

        system_inputs = Chains.systemInputs(instruction=instruction)
        app_type = Chains.appType(instruction=instruction)

        yield {
            "stage": "plan",
            "completed": False,
            "percentage": 10,
            "done": False,
            "message": "Plan creation has started...",
            "failed": False,
        }

        plan = Chains.planWithInputs(
            instruction=instruction, system_inputs=system_inputs, app_type=app_type
        )

        yield {
            "stage": "plan",
            "completed": True,
            "percentage": 20,
            "done": False,
            "message": "Plan has been generated.",
            "failed": False,
        }

        sleep(1)

        yield {
            "stage": "plan_controlling",
            "completed": True,
            "percentage": 25,
            "done": False,
            "message": "Plan is being controlled.",
            "failed": False,
        }

        plan_controller_result = Chains.planController(plan=plan, app_type=app_type)

        for _ in trange(self.max_steps):
            if not plan_controller_result["valid"]:
                plan = Chains.planRefiner(
                    instruction=instruction,
                    plan=plan,
                    feedback=plan_controller_result["feedback"],
                    app_type=app_type,
                )
                plan_controller_result = Chains.planController(
                    plan=plan, app_type=app_type
                )
            else:
                break

        if not plan_controller_result["valid"]:
            yield {
                "stage": "plan",
                "completed": False,
                "percentage": 100,
                "done": False,
                "message": self.FAIL_MESSAGE,
                "failed": True,
            }

        else:

            yield {
                "stage": "task",
                "completed": False,
                "percentage": 30,
                "done": False,
                "message": "Task generation has started...",
                "failed": False,
            }

            task_list = Chains.tasks(
                instruction=instruction, plan=plan, app_type=app_type
            )

            yield {
                "stage": "task",
                "completed": True,
                "percentage": 50,
                "done": False,
                "message": "Tasks have been generated.",
                "tasks": task_list,
                "failed": False,
            }

            sleep(1)

            yield {
                "stage": "task_controlling",
                "completed": True,
                "percentage": 55,
                "done": False,
                "message": "Tasks are being controlled.",
                "failed": False,
            }

            task_controller_result = Chains.taskController(
                tasks=task_list, app_type=app_type
            )

            for _ in trange(self.max_steps):
                if not task_controller_result["valid"]:
                    try:
                        task_list = Chains.refineTasks(
                            instruction=instruction,
                            tasks=task_list,
                            feedback=task_controller_result["feedback"],
                            app_type=app_type,
                        )
                        task_controller_result = Chains.taskController(
                            tasks=task_list, app_type=app_type
                        )
                    except Exception as e:
                        print(e)
                        if "16k" in Chains.model:
                            break
                        print(
                            "To increase the window size, changing model type to gpt-3.5-turbo-16k-0613"
                        )
                        Chains.setModel("gpt-3.5-turbo-16k-0613")
                else:
                    break

            if not task_controller_result["valid"]:

                yield {
                    "stage": "task",
                    "completed": False,
                    "percentage": 100,
                    "done": False,
                    "message": self.FAIL_MESSAGE,
                    "failed": True,
                }

            else:

                code_snippets = init(title)

                sleep(1)

                yield {
                    "stage": "draft",
                    "completed": False,
                    "percentage": 60,
                    "done": False,
                    "message": "Converting tasks to code snippets...",
                }

                num_of_tasks = len(task_list)

                for i, task in enumerate(task_list):
                    code = getCodeSnippet(task, code_snippets, self.max_steps)
                    code = "#" + task["description"] + "\n" + code
                    code_snippets += code
                    yield {
                        "stage": "draft",
                        "completed": i + 1 == num_of_tasks,
                        "percentage": 60 + int(20 * (i + 1) / num_of_tasks),
                        "done": False,
                        "message": f"{i+1}/{num_of_tasks} tasks have been converted to code",
                        "code": code,
                    }

                sleep(1)

                yield {
                    "stage": "draft",
                    "completed": False,
                    "percentage": 85,
                    "done": False,
                    "message": "Code snippets are being combined...",
                }

                chat_app = any(
                    [
                        task["task_type"] in ["ui_input_chat", "ui_output_chat", "chat"]
                        for task in task_list
                    ]
                )

                if chat_app:
                    final_code = code_snippets
                    sleep(1)
                else:
                    function_names = getFunctionNames(code_snippets)
                    draft_code = Chains.combine_v2(
                        code_snippets=code_snippets, function_names=function_names
                    )
                    import_statements = Chains.imports(code_snippets=code_snippets)
                    if f"st.title('{title}')" not in draft_code:
                        draft_code = f"\nst.title('{title}')\n" + draft_code
                    final_code = import_statements + draft_code

                # finalize the format
                final_code = final_code.replace("\t", 4 * " ")
                final_code = autopep8.fix_code(final_code)

                yield {
                    "stage": "final",
                    "completed": True,
                    "percentage": 100,
                    "done": True,
                    "message": "Final code has been generated. Directing to the demo page...",
                    "code": final_code,
                }
