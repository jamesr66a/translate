#!/usr/bin/env python3

from optparse import OptionParser

from pytorch_translate.research.unsupervised_morphology import unsupervised_morphology


def get_arg_parser():
    parser = OptionParser()
    parser.add_option(
        "--train-file",
        dest="train_file",
        help="Raw text as training data.",
        metavar="FILE",
        default=None,
    )
    parser.add_option(
        "--model",
        dest="model_path",
        help="Path to the model file.",
        metavar="FILE",
        default=None,
    )
    parser.add_option(
        "--iter",
        type="int",
        dest="em_iter",
        help="Number of EM training epochs.",
        default=30,
    )
    parser.add_option(
        "--num-cpu",
        type="int",
        dest="num_cpus",
        help="Number of CPUs for parallel training.",
        default=10,
    )
    parser.add_option(
        "--input",
        dest="input_file",
        help="Raw text to segment.",
        metavar="FILE",
        default=None,
    )
    parser.add_option(
        "--output",
        dest="output_file",
        help="Segmented output file.",
        metavar="FILE",
        default=None,
    )
    parser.add_option(
        "--no-affix-symbol",
        action="store_false",
        dest="add_affix_symbols",
        default=True,
    )
    parser.add_option(
        "--save-checkpoint", action="store_true", dest="save_checkpoint", default=False
    )
    parser.add_option(
        "--smooth-const",
        type="float",
        help="Constant float value for smoothing probabilities.",
        dest="smooth_const",
        default=2,
    )
    parser.add_option(
        "--normal-init",
        action="store_true",
        help="Initialize parameters with samples from normal distribution.",
        dest="normal_init",
        default=False,
    )
    parser.add_option(
        "--normal-mean",
        type="float",
        help="Mean for the normal distribution in initialization.",
        dest="normal_mean",
        default=2,
    )
    parser.add_option(
        "--hard-em", action="store_true", dest="use_hardEM", default=False
    )
    parser.add_option(
        "--normal-stddev",
        type="float",
        help="Standard deviation for the normal distribution in initialization.",
        dest="normal_stddev",
        default=1,
    )
    parser.add_option(
        "--no-morph-likeness",
        action="store_false",
        help="Turn off morph likeness based on perplexity.",
        dest="use_morph_likeness",
        default=True,
    )
    parser.add_option(
        "--perplexity-threshold",
        type="float",
        help="Perplexity threshold in affix likeness equation.",
        dest="perplexity_threshold",
        default=10,
    )
    parser.add_option(
        "--length-threshold",
        type="float",
        help="Length threshold in stem likeness equation.",
        dest="length_threshold",
        default=3,
    )
    parser.add_option(
        "--perplexity-slope",
        type="float",
        help="Perplexity slope in affix likeness equation.",
        dest="perplexity_slope",
        default=1,
    )
    parser.add_option(
        "--length-slope",
        type="float",
        help="Length slope in stem likeness equation.",
        dest="length_slope",
        default=2,
    )
    parser.add_option(
        "--investigate",
        action="store_true",
        dest="investigate",
        help="Manually investigate param values for error analysis.",
        default=False,
    )
    return parser


if __name__ == "__main__":
    arg_parser = get_arg_parser()
    options, args = arg_parser.parse_args()
    if options.train_file is not None and options.model_path is not None:
        model = unsupervised_morphology.UnsupervisedMorphology(
            input_file=options.train_file,
            smoothing_const=options.smooth_const,
            use_normal_init=options.normal_init,
            normal_mean=options.normal_mean,
            normal_stddev=options.normal_stddev,
            use_hardEM=options.use_hardEM,
            use_morph_likeness=options.use_morph_likeness,
            perplexity_threshold=options.perplexity_threshold,
            perplexity_slope=options.perplexity_slope,
            length_threshold=options.length_threshold,
            length_slope=options.length_slope,
        )
        print("Number of training words", len(model.params.word_counts))
        model.expectation_maximization(
            options.em_iter,
            options.num_cpus,
            options.model_path if options.save_checkpoint else None,
        )
        if not options.save_checkpoint:
            model.params.save(options.model_path)

    if (
        options.input_file is not None
        and options.output_file is not None
        and options.model_path is not None
    ):
        model = unsupervised_morphology.MorphologyHMMParams.load(options.model_path)
        segmentor = unsupervised_morphology.MorphologySegmentor(model)
        segment_cache = {}
        writer = open(options.output_file, "w", encoding="utf-8")
        with open(options.input_file, "r", encoding="utf-8") as input_stream:
            for line in input_stream:
                output = []
                for word in line.strip().split():
                    if word not in segment_cache:
                        segmented = segmentor.segment_word(
                            word, add_affix_symbols=options.add_affix_symbols
                        )
                        segment_cache[word] = segmented
                    output.append(segment_cache[word])
                writer.write(" ".join(output) + "\n")
        writer.close()

    if options.investigate and options.model_path is not None:
        model = unsupervised_morphology.MorphologyHMMParams.load(options.model_path)
        segmentor = unsupervised_morphology.MorphologySegmentor(model)

        while True:
            message = " ".join(
                [
                    "input options: 1) e [str] for emission probs,",
                    "2) t for transition params,",
                    "3) l [str] for likeness params,",
                    "4) s [str] for segmenting word:\n",
                ]
            )
            input_command = input(message).strip().split()

            if len(input_command) > 1 and (
                input_command[0] == "e" or input_command[0] == "l"
            ):
                substr = input_command[1]
                lookup = (
                    model.morph_emit_probs
                    if input_command[0] == "e"
                    else model.morph_likeness
                )
                prefix_val = (
                    lookup["prefix"][substr] if substr in lookup["prefix"] else 0
                )
                stem_val = lookup["stem"][substr] if substr in lookup["stem"] else 0
                suffix_val = (
                    lookup["suffix"][substr] if substr in lookup["suffix"] else 0
                )
                print(prefix_val, stem_val, suffix_val)
            elif len(input_command) > 1 and input_command[0] == "s":
                word = input_command[1]
                segmented = segmentor.segment_word(word, add_affix_symbols=True)
                print(segmented)
            elif input_command[0] == "t":
                print(model.affix_trans_probs)
