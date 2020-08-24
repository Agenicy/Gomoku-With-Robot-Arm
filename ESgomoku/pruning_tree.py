import math
from evaluate_points import Judge, JudgeArray, Score, np # np will be numpy or cupy

from copy import deepcopy

counter = 0

class Node(object):
    value = 0
    score = None
    child = []
    
    # ? parent 的必要性?
    parent = None
    step = []
    
    def __init__(self, board = [], loc = None, 
                 parent = None, deep = 0, isAlpha = True, score = None, 
                 judge = None, alphaIsBlack = False):
        """新增一個節點
        
        Keyword Arguments:
            board {list2D} -- [敵方落子位置, 我方落子位置] (default: {[]})
            loc {list} -- 敵方落子於 location [x, y] (default: {None})
            parent {Node} -- 父節點 (default: {None})
            deep {int} -- 搜索深度，每次建立 child 傳入時要 -1 (default: {0})
            isAlpha {bool} -- 本節點為 alpha 節點 (default: {True})
            score {Score}  -- 盤勢分數計算器 (default: {None})
            judge {judge} -- 評估器與其值 (default: {None})
            alphaIsBlack {bool} -- alpha 玩家是否執黑 (default: {False})
        """     
        global counter
        counter += 1
        #*print(f'[new node({counter})] -- deep = {deep}')
        
        self.parent = parent
        self.score = Score(copyFrom = score) # copy
        self.deep = deep
        
        #*print(f'pruning_tree / enemy loc at: {loc}')
        # about judge
        self.board = deepcopy(board)
        self.judge = Judge(copyFrom = judge) # copy
        if deep > 0:
            self.judge.AddSolveRange(board, loc)
            # print(f'[node] solverange = {self.judge.solveRange}')
        
        self.loc = loc
        
        self.isAlpha = isAlpha
        self.alphaIsBlack = alphaIsBlack
        
        if isAlpha:
            # 提早終止的回傳值
            self.terminateValue = 0
        else:  
            self.terminateValue = 1
            
        # isAlpha XNOR alphaIsBlack -> 本節點執黑
        if isAlpha == alphaIsBlack:
            # 執黑
            self.IsBlack = True
            # 玩家順序
            self.playerNum = 0
        else:
            # 執白
            self.IsBlack = False
            self.playerNum = 1
        
        
    def GetValue(self):
        """回傳 (對於Alpha的) 盤勢分數，應該只有最後的alpha節點 (的 beta 半節點) 會呼叫"""
        if self.isAlpha:
            # parent is Beta
            raise Exception('Beta 節點嘗試取得分數!')
        return self.score.GetScore(selfIsBlack = self.IsBlack)

    def Run(self):
        """節點開始運作，回傳節點分數
        
        Returns:
            value -- 節點盤勢分數
            step -- 應該落子的最佳位置
        """
        
        #*print('pruning_tree / node.run() ')
        
        # 計算節點的 pattern 並記下分數
        solution, isWin = self.judge.Solve_and_DetectWin(self.board, self.loc)
        
        #* 落子的一方勝利，終止運算
        if isWin:
            #//print(f'terminate with value = {self.terminateValue}')
            
            # is root
            if self.parent is None:
                print('root return')
                return [0, 0], self.terminateValue
            
            return self.terminateValue, True
        
        #* 沒分出勝負 -> 紀錄分數
        #*print('pruning_tree / node.score.add() ')
        self.score.Add(solution, selfIsBlack = self.IsBlack)
        
        
        #> 如果達到搜索深度 = 本節點單純用於回傳分數
        if self.deep == 0:
            val = self.GetValue()
            #* print(f'deep end. return {self.loc} : {val}')
            return val, False
        else:
            print(f'searching at {self.loc}')
        
        #> 還沒達到搜索深度 -> 生成 child
        #*print('searching...')
        for step in self.judge.solveRange:
            
            child = Node(board=deepcopy(self.board), loc=step,
                         parent=self, deep=self.deep - 1, isAlpha=not self.isAlpha, score=self.score,
                         judge=self.judge, alphaIsBlack=self.alphaIsBlack)
            
            # 取得 child 的分數( 他自己算，或是從他 child 裡面找 )
            value, is_Terminated = child.Run()
            print(f'get child value: {step} = {value}')
            
            # 檢查 child 是否被剪枝
            if value is None:
                # 剪枝，這個 step 不好 -> 跳過這一輪
                continue
            
            # 剪枝
            if self.isAlpha:
                # alpha
                
                if not self.parent is None:
                    # leaf
                    if value > self.parent.value:
                        # 對 beta 來說，這個節點比已經找過的還差 -> beta 不會選這裡，剪枝
                        print(f'alpha cutoff : {value} > {self.parent.value}')
                        return None
                else:
                    # root
                    #? nothing?
                    pass
                    
                if value >= self.value:
                    # alpha 要選擇最大值的節點
                    #// print(f'選擇已更新: {step} with value = {value}')
                    self.value = value
                    self.step = step
                    
            else:
                # beta
                # 必為 leaf 節點
                
                if value <= self.parent.value:
                    # 對 alpha 來說，這個節點比已經找過的還差 -> alpha 不會選這裡，剪枝
                    print(f'beta cutoff : {value} < {self.parent.value}')
                    return None
                
                if value < self.value:
                    # beta 要選擇最小值的節點
                    self.value = value
                
                if is_Terminated:
                    break

        # root
        if self.parent is None:
        
            #> print
            print('root return')
            return self.step, self.score.whiteScore
        else:
            #搜尋完畢，回傳
            return self.value, False
                            
                
            

class alpha_beta_tree(object):
    '''
        > 總盤勢分數 = 我方盤勢分數 * (進攻係數) - 敵方盤勢分數
        > 我方盤勢分數 = 整個版面上我方 pattern 分數 * [(達成權值)] - 被敵方阻擋的 pattern 分數 * [(阻擋權值)]
        > 敵方盤勢分數 = 整個版面上敵方 pattern 分數 * [(達成權值)] - 被我方阻擋的 pattern 分數 * [(阻擋權值)]
            - 從第一手開始持續記錄各種pattern數量     
        [第零層]
            玩家落子，是為 root
        [第一層 - Alpha]
            從敵方落子後開始，計算第一次候選步
                ! 此時節點 board = [ [AI], [Player] ]
                - 每個候選步都是一個節點，節點的 board 為候選步落子後的盤勢
                ! 此時 board 順序未變
                - 如果勝利則停止計算 並回傳
                - 如果未勝利，按照候選步更新可落子區域( judge.solvePoint )，並取得新的 solveRange
                - 按照新的 solveRange 計算第二次候選步
        [第二層 - Beta]
            計算第二次候選步
                ! 此時節點 board = [ [Player], [AI] ]
                - 方法與第一次相同
                - 按照新的 solveRange 計算第三次候選步
        [第三層 - Alpha]
            計算第三次候選步
                ! 此時節點 board = [ [AI], [Player] ]
                - 方法與第一次相同
                - 因為抵達深度盡頭 ( deep = 0 )，不再延伸子樹
                * 現在位於「第一個抵達深度盡頭」的節點
                - 回傳自己的盤勢分數 value
        [剪枝與持續搜尋]
                * 現在回到 parent ( 第二層 )
                - 檢查 child.value 是否「小於」 alphaValue ( 因為第二層是beta，他會取AI分數的最小值 )
                    > 是
                    - 修改 alphaValue = child.value
                - 由於 for 迴圈，這個動作會持續到所有節點都走過一次
                - 得到自己該選擇的最佳位置
                - 回傳最後的盤勢分數
                
                * 現在回到 parent ( 第一層 )
                - 檢查 child.value 是否「大於」 alphaValue ( 第一層是alpha )
                    > 是
                    - 修改 alphaValue = child.value
                    - 紀錄 stepChoose = 候選步
                - 由於 for 迴圈，這個動作會持續到所有節點都走過一次
                
                [loop]
                * 由於迴圈，現在進入 child ( 第二層，第二棵子樹 )
                /* 現在會開始剪枝 */
                - [計算新的第三次候選步]
                - 由於 for 迴圈，會持續收到child.value
                /* 如果收到了比之前更小的總和盤勢分數，代表進入第二層的這一步對AI不利，因此放棄 */
                - 檢查 child.value 是否小於 alphaValue
                    > 是
                    - 放棄搜尋，回傳 None
                > 最大的 child.value 比 alphaValue 大
                - 回傳最大的 child.value， parent 端會做後續處理
                
                [loop]
                * 又回到 parent ( 第一層 )
                - 檢查 child.value 是否大於 alphaValue
                    > 是
                    - 修改 alphaValue = child.value
                    - 紀錄 stepChoose = 候選步
                    > 否
                    - 跳過
                - 繼續尋找下一棵子樹
        [結束]
        回傳 stepChoose        
    '''
    
    def __init__(self, board, enemyLastLoc, deep, score, judge, alphaIsBlack):
        """[第零層]\n
        玩家落子，是為 root"""
        #> print
        print(r'[tree]')
        self.root = Node(board=deepcopy(board), loc=enemyLastLoc,
                         parent=None, deep=deepcopy(deep), isAlpha=True, score=deepcopy(score),
                         judge=deepcopy(judge), alphaIsBlack=alphaIsBlack)
    
    def Run(self):
        """
        開始運作
        """
        global counter
        import time
        tStart = time.clock()
        ret, scoreRet = self.root.Run()
        tEnd = time.clock()
        print(f'Tree done with {counter} nodes. Use {tEnd - tStart} CPU clock time.')
        print(scoreRet)
        return ret
