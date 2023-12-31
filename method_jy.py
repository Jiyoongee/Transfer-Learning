# -*- coding: utf-8 -*-
"""Method_JY.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1TNvc95_HGaJU5O859wbEdhk17hiYJUBo
"""

import numpy as np
import torch

def gradNorm(net, alpha, layer, dataloader, lr1, lr2, epochs, log = False):
  # log 초기화
  if log:
      log_loss = []
      log_weights = []
  # optimizer 세팅
  optimizer1 = torch.optim.Adam(net.parameters, lr = lr1)
  # 훈련
  iters = 0
  net.train()
  for epoch in range(epochs):
      # 데이터 로드
      for batch in dataloader:
        # cuda
        if next(net.parameters()).is_cuda:
          batch = [d.cuda() for d in batch]
        # forward pass
        loss = net(*batch)
        # 초기화
        if iters == 0:
          # 가중치 초기화
          weights = torch.ones_like(loss)
          weights = torch.nn.Parameter(weights)
          T = weights.sum().detach() # 가중치 합
          # 가중치를 위한 optimizer 설정
          optimizer2 = torch.optim.Adam([weights], lr = lr2)
          # L(0) 설정
          l0 = loss.detach()  # detach 의 역할 알아보기
        # weighted loss 계산
        weighted_loss = weights @ loss
        # 네트워크의 gradient 초기화
        optimizer1.zero_grad()
        # weighted loss 를 위한 backward pass
        weighted_loss.backward(retain_graph=True)  # retain_graph 의 역할 확인
        # 각 태스크에 대한 gradient 의 L2 Norm 계산
        gw = []
        for i in range(len(loss)):
            dl = torch.autograd.grad(weights[i]*loss[i], layer.parameters(), retain_graph = True, create_graph = True)[0]
            gw.append(torch.norm(dl))
        gw = torch.stack(gw)  # stack 의 역할
        # 태스크 마다 loss ratio 계산
        loss_ratio = loss.detach() / l0
        # 태스크 마다 relative inverse training rate 계산
        rt = loss_ratio / loss_ratio.mean()    # 논문 식 반영
        # 평균 gradient norm 계산
        gw_avg = gw.mean().detach()
        # GradNorm loss 계산
        constant = (gw_avg * rt ** alpha).detach()   # 논문에서 해당 부분 찾기
        gradnorm_loss = torch.abs(gw - constant).sum()
        # 가중치의 gradient 초기화
        optimizer2.zero_grad()
        # GradNorm 의 backward process
        gradnorm_loss.backward()
        # 가중치와 loss 로깅
        if log:
            # 각 태스크별 가중치
            log_weights.append(weights.detach().cpu().numpy().copy())
            # 태스크 정규화 loss
            log_loss.append(loss_ratio.detach().cpu().numpy().copy())
        # 모델 가중치 업데이트
        optimizer1.step()
        # loss 가중치 업데이트
        optimizer2.step()
        # 가중치 재정규화
        weights = (weights / weights.sum() * T).detach()  # 논문에서 해당부분 찾기
        weights = torch.nn.Parameter(weights)
        optimizer2 = torch.optim.Adam([weights], lr = lr2)
        # iters 업데이트
        iters += 1
  # get logs
  if log:
      return np.stack(log_weights), np.stack(log_loss)