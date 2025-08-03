#!/usr/bin/env python3
"""Riffusion Prompt Architect demo.
Generates structured prompts in three modes: free, selective, expansive.
This is a simplified example inspired by the analysis discussion.
"""
import argparse
import textwrap


def free_mode(text):
    """Generate a prompt from minimal genre/vibe keywords."""
    base = text
    clarifiers = (
        "Add tempo or era descriptions?",
        "Consider specifying instrumentation or mood",
    )
    angles = {
        "Rhythm": "syncopated percussion loops, rapid snare rolls",
        "Texture": "rainforest ambiance, vinyl crackle",
        "Melodic": "tribal flute motifs over distorted bass",
    }
    final_prompt = f"{base}, {', '.join(angles.values())}, 120 BPM, heavy sub-bass frequencies"
    return final_prompt, clarifiers


def selective_mode(reference):
    """Reverse engineer a reference track into a prompt."""
    dimensions = {
        "Genre": "Progressive House",
        "Chord Progression": "Ascending minor-key arpeggios",
        "Instruments": "Serum synths, TR-909 kicks",
        "Tempo": "128 BPM",
        "Mix": "Clean highs, deep sub-bass",
        "Techniques": "Automation swells, sidechain compression",
        "Vibe": "Hypnotic euphoria",
    }
    clarifier = "Adjust tempo or add new elements?"
    prompt_parts = [dimensions[d] for d in dimensions]
    final_prompt = f"{', '.join(prompt_parts)} (inspired by {reference})"
    return final_prompt, clarifier


def expansive_mode(url, extra):
    """Combine URL metadata with extra descriptors."""
    domain = url.split('/')[2] if '://' in url else url
    base = f"Audio from {domain} suggests gritty FM synths, TR-808 drums"
    variation = f"{extra}" if extra else "ethereal vocals"
    experimental = "glitchy tape stops between phrases"
    final_prompt = f"{base}, {variation}, {experimental}, 120 BPM"
    return final_prompt


def main():
    parser = argparse.ArgumentParser(description="Generate Riffusion prompts")
    parser.add_argument("mode", choices=["free", "selective", "expansive"], help="operation mode")
    parser.add_argument("input", nargs="*", help="text or URL depending on mode")
    args = parser.parse_args()

    if args.mode == "free":
        if not args.input:
            parser.error("free mode requires a description")
        text = " ".join(args.input)
        prompt, clarifiers = free_mode(text)
        print("Prompt:")
        print(prompt)
        print("\nClarifiers:")
        for c in clarifiers:
            print(f"- {c}")
    elif args.mode == "selective":
        if not args.input:
            parser.error("selective mode requires a reference")
        reference = " ".join(args.input)
        prompt, clarifier = selective_mode(reference)
        print("Prompt:")
        print(prompt)
        print("\nClarifier:")
        print(clarifier)
    elif args.mode == "expansive":
        if not args.input:
            parser.error("expansive mode requires a URL and optional extra descriptors")
        url = args.input[0]
        extra = " ".join(args.input[1:]) if len(args.input) > 1 else ""
        prompt = expansive_mode(url, extra)
        print("Prompt:")
        print(prompt)

if __name__ == "__main__":
    main()
