from app.models.project_context import ProjectContext

def create_system_prompt(context: ProjectContext) -> str:
    """
    Generates a system prompt for Gemini based on the project context.
    """
    
    prompt_lines = [
        "You are the Lume Architect, a world-class expert in software development with a specialization in the following technologies: {tech_stack}.",
        "You are working on a project with the following description: '{description}'.",
    ]

    if context.venv_path:
        prompt_lines.append("The project's virtual environment is located at: '{venv_path}'.")

    prompt_lines.extend([
        "
Your task is to provide expert guidance, code, and solutions.",
        "Always consider the project's context and technology stack when formulating your responses."
    ])
    
    return "
".join(prompt_lines).format(
        tech_stack=context.tech_stack,
        description=context.description,
        venv_path=context.venv_path or "Not specified"
    )

if __name__ == '__main__':
    # Example Usage
    project_ctx = ProjectContext(
        description="A new IDE for Python and AI development, designed to be intuitive and powerful.",
        tech_stack="Python, PyQt6, Google Gemini API",
        venv_path="/path/to/project/.venv"
    )
    
    system_prompt = create_system_prompt(project_ctx)
    print("--- Generated System Prompt ---")
    print(system_prompt)

    # Example with missing venv path
    project_ctx_no_venv = ProjectContext(
        description="A simple web scraper.",
        tech_stack="Python, BeautifulSoup"
    )
    print("
--- Prompt with missing venv ---")
    print(create_system_prompt(project_ctx_no_venv))
