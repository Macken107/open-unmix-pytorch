import argparse
import musdb
import museval
import test
import multiprocessing
import functools
from pathlib import Path
import torch


def separate_and_evaluate(
    track,
    targets,
    model_name,
    niter,
    alpha,
    softmask,
    output_dir,
    device='cpu'
):
    print(track.name, track.duration)
    estimates = test.separate(
        audio=track.audio,
        targets=targets,
        model_name=model_name,
        niter=niter,
        alpha=alpha,
        softmask=softmask,
        device=device
    )
    if args.outdir:
        mus.save_estimates(estimates, track, args.outdir)

    scores = museval.eval_mus_track(
        track, estimates, output_dir=args.evaldir
    )
    print(scores)
    return scores


if __name__ == '__main__':
    # Training settings
    parser = argparse.ArgumentParser(
        description='MUSDB18 Evaluation',
        add_help=False
    )

    parser.add_argument(
        '--targets',
        nargs='+',
        default=['vocals', 'drums', 'bass', 'other'],
        type=str,
        help='provide targets to be processed. \
              If none, all available targets will be computed'
    )

    parser.add_argument(
        '--model',
        default='umxhq',
        type=str,
        help='path to mode base directory of pretrained models'
    )

    parser.add_argument(
        '--outdir',
        type=str,
        default="OSU_RESULTS",
        help='Results path where audio evaluation results are stored'
    )

    parser.add_argument(
        '--evaldir',
        type=str,
        help='Results path for museval estimates'
    )

    parser.add_argument(
        '--root',
        type=str,
        help='Path to MUSDB18'
    )

    parser.add_argument(
        '--subset',
        type=str,
        help='MUSDB subset (`train`/`test`)'
    )

    parser.add_argument(
        '--cores',
        type=int,
        default=1
    )

    parser.add_argument(
        '--no-cuda',
        action='store_true',
        default=False,
        help='disables CUDA inference'
    )

    parser.add_argument(
        '--is-wav', 
        action='store_true', default=False,
        help='flags wav version of the dataset'
    )

    args, _ = parser.parse_known_args()
    args = test.inference_args(parser, args)

    use_cuda = not args.no_cuda and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    mus = musdb.DB(
        root=args.root, 
        download=args.root is None,
        subsets=args.subset,
        is_wav=args.is_wav
    )
    if args.cores > 1:
        pool = multiprocessing.Pool(args.cores)
        results = list(
            pool.imap_unordered(
                func=functools.partial(
                    separate_and_evaluate,
                    model_name=args.model,
                    niter=args.niter,
                    alpha=args.alpha,
                    softmask=args.softmask,
                    output_dir=args.evaldir,
                    device=device
                ),
                iterable=mus.tracks,
                chunksize=1
            )
        )

        pool.close()
        pool.join()
    else:
        for track in mus.tracks:
            separate_and_evaluate(
                track,
                targets=args.targets,
                model_name=args.model,
                niter=args.niter,
                alpha=args.alpha,
                softmask=args.softmask,
                output_dir=args.evaldir,
                device=device
            )
