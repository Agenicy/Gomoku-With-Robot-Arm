using UnityEngine;
using System.Collections;
using UnityEngine.Events;
using System;

public class ScreenClickedEvent : MonoBehaviour
{
	/*
	 * 如果按下按鍵時間小於clickTimeRange，則廣播ScreenClicked事件給訂閱者
	 * 使用時，如會改變遊戲狀態(如暫停、查看紀錄等)，請修改Mode字串
	 * 承上，使用後請改回default
	 */
	 
	public event EventHandler ScreenClicked;

	[Header("目前遊戲狀態")]
	public string mode = "default";

	[SerializeField]
	private bool mouseClick;//按下按鈕時改變為true
	[SerializeField]
	private float clickTime;
	const float clickTimeRange = 0.2f;//判斷為點擊而非滑動的最長時間

	void Start()
	{
		mouseClick = false;

		//手機禁止多點觸碰
		Input.multiTouchEnabled = false;
	}

	void Update()
	{

		//判斷平台
#if !UNITY_EDITOR && (UNITY_IOS || UNITY_ANDROID)
        MobileInput (); 
#else
		DeskopInput();
#endif

	}


	//////////////////////////////private//////////////////////////////////
	void DeskopInput()
	{
		//滑鼠左鍵
		if (Input.GetMouseButton(0))
		{
			mouseClick = true;

			clickTime += Time.deltaTime;//開始計時

		}
		else
		{
			if (mouseClick)
			{
				if (clickTime < clickTimeRange)
				{
					Click();
				}
				mouseClick = false;
				clickTime = 0;
			}
		}
	}

	void MobileInput()
	{
		if (Input.touchCount <= 0)
			return;

		//1個手指觸碰螢幕
		if (Input.touchCount == 1)
		{
			clickTime += Time.deltaTime;//開始計時

			//開始觸碰
			if (Input.touches[0].phase == TouchPhase.Began)
			{
				clickTime = 0;
				mouseClick = true;
			}

			//手指離開螢幕
			if (Input.touches[0].phase == TouchPhase.Ended && Input.touches[0].phase == TouchPhase.Canceled)
			{
				if (clickTime < clickTimeRange)
				{
					Click();
				}
				mouseClick = false;
				clickTime = 0;
			}
		}
	}

	private void Click()
	{
		//Debug.Log("Click Event!");
		if (ScreenClicked != null)
			ScreenClicked(this, EventArgs.Empty);
	}
}
