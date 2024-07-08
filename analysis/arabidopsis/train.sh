WANDB_PROJECT=GPN_Arabidopsis_multispecies python -m gpn.ss.run_mlm --do_train --do_eval \
    --fp16 --report_to wandb --prediction_loss_only True --remove_unused_columns False \
    --dataset_name output/merged_dataset/512/256/True/balanced --tokenizer_name gonzalobenegas/tokenizer-dna-mlm \
    --soft_masked_loss_weight_train 0.1 --soft_masked_loss_weight_evaluation 0.0 \
    --weight_decay 0.01 --optim adamw_torch \
    --dataloader_num_workers 16 --preprocessing_num_workers 32 --seed 42 \
    --save_strategy steps --save_steps 10000 --evaluation_strategy steps --eval_steps 10000 --logging_steps 10000 --max_steps 120000 --warmup_steps 1000 \
    --learning_rate 1e-3 --lr_scheduler_type constant_with_warmup \
    --run_name ConvNet_batch2048_weight0.1 --output_dir /scratch/users/gbenegas/checkpoints/GPN_Arabidopsis_multispecies/ConvNet_batch2048_weight0.1 --model_type ConvNet \
    --per_device_train_batch_size 2048 --per_device_eval_batch_size 2048 --gradient_accumulation_steps 1 \

# note: there's a bug in huggingface trainer with iterable dataset, the per_device_*_batch_size is interpreted as total batch size
