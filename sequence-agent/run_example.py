from git_sequence_agent.graph import build_graph

if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke({
        "git_url": "https://github.com/mdtalalwasim/Spring-Boot-REST-API.git",
        "output_path": "sequence-diagram.md",
    })
    print(result["output_path"])
    print(result["mermaid_code"])
