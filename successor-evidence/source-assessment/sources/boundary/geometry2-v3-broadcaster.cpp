
#include "rclcpp/rclcpp.hpp"
#include <tf2_ros/transform_broadcaster.h>

class BroadcasterNode : public rclcpp::Node
{
public:
	explicit BroadcasterNode(const rclcpp::NodeOptions & options) :
		BroadcasterNode("broadcaster", options)
	{}
	explicit BroadcasterNode(const std::string & name, const rclcpp::NodeOptions & options) :
		Node(name, options),
		thread_running_(true)
	{
		tf_broadcaster_ = std::make_shared<tf2_ros::TransformBroadcaster>(this);
		transform_thread_.reset(new std::thread([&]()
		{
			rclcpp::Rate r(25);
			while(thread_running_)
			{
				geometry_msgs::msg::TransformStamped msg;
				msg.child_frame_id = "base_link";
				msg.header.frame_id = "odom";
				// add 100 ms delay (camera delay of 60 ms + 40 ms vo)
				msg.header.stamp = now() - rclcpp::Duration::from_seconds(0.1);
				msg.transform.rotation.w = 1.0;
				tf_broadcaster_->sendTransform(msg);
				r.sleep();
			}
		}));
	}
	virtual ~BroadcasterNode() {
		thread_running_ = false;
		transform_thread_->join();
	}

private:
	std::shared_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
	std::shared_ptr<std::thread> transform_thread_;
	bool thread_running_;
};

int main(int argc, char** argv)
{
	rclcpp::init(argc, argv);
	rclcpp::spin(std::make_shared<BroadcasterNode>(rclcpp::NodeOptions()));
	rclcpp::shutdown();
	return 0;
}
